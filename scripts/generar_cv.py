"""Genera el CV en PDF, uno por idioma, desde data/perfil.yml (fuente única).

Uso:  python3 scripts/generar_cv.py
Requiere: jinja2, pyyaml y playwright con Chromium (ver scripts/requisitos.txt).
Salida: los PDF de cv.archivo en data/perfil.yml (cv/jose-hugo-meza-cv-es.pdf y cv/jose-hugo-meza-cv-en.pdf),
        tamaño carta y de una sola página cada uno.

Antes de escribir nada valida la fuente con las mismas reglas del sitio (scripts/generar.py) más las del CV,
y comprueba que cada idioma quepa en una página. Si algo falla, no escribe ningún PDF.
"""
import datetime
import pathlib
import re
import sys
import tempfile

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.exceptions import UndefinedError
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True  # importar generar.py no debe dejar scripts/__pycache__ en el repo
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generar import IDIOMAS, RAIZ, es_traducible, validar  # noqa: E402  (mismas reglas que el sitio)

# Hoja carta y márgenes, en pulgadas. El pie del CV (una línea pequeña) ocupa el fondo del área útil,
# así que el texto principal termina a ~0.6 in del borde inferior.
CARTA = (8.5, 11.0)
MARGENES = {"top": 0.45, "right": 0.5, "bottom": 0.3, "left": 0.5}
FUENTES = ("space-mono-400.woff2", "space-mono-700.woff2", "titillium-web-400.woff2", "titillium-web-600.woff2")
CLAVES_CV = ("archivo", "documento", "titulo_profesional", "secciones", "tecnologias", "actualizado", "meses")
SECCIONES_CV = ("perfil", "experiencia", "premios", "proyectos", "formacion", "habilidades")

# Fuerza la carga de todas las fuentes y devuelve las que fallaron (si una falla, Chromium usaría otra sin avisar).
JS_FUENTES = """async () => {
  const caras = [...document.fonts];
  const r = await Promise.allSettled(caras.map(f => f.load()));
  return caras.filter((f, i) => r[i].status !== "fulfilled").map(f => `${f.family} ${f.weight}`);
}"""
# Alto natural del contenido en px CSS, sin el alto mínimo que empuja el pie al fondo de la hoja.
JS_ALTO = """() => {
  const cv = document.querySelector(".cv");
  cv.style.minHeight = "0";
  const alto = cv.getBoundingClientRect().height;
  cv.style.minHeight = "";
  return alto;
}"""


def url_visible(url):
    """Texto legible de un enlace: 'https://www.linkedin.com/in/x/' → 'linkedin.com/in/x'."""
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def junto(texto):
    """Pega « · », « – » y « — » a la palabra anterior para que ningún renglón empiece con un separador."""
    for sep in ("·", "–", "—"):
        texto = texto.replace(f" {sep} ", f"\u00a0{sep} ")
    return texto


def validar_cv(s):
    """Reglas propias del CV. Devuelve una lista de problemas; vacía si todo está bien."""
    cv = s.get("cv") or {}
    faltan = [c for c in CLAVES_CV if c not in cv]
    if faltan:
        return [f"Falta cv.{c} (texto del CV)" for c in faltan]
    errores = [f"Falta el título de sección cv.secciones.{c}" for c in SECCIONES_CV if c not in cv["secciones"]]
    for lang in IDIOMAS:
        if not str(cv["archivo"].get(lang, "")).endswith(".pdf"):
            errores.append(f"cv.archivo.{lang} debe ser una ruta que termine en .pdf")
        if len(cv["meses"].get(lang, [])) != 12:
            errores.append(f"cv.meses.{lang} debe tener los 12 meses")
    if cv["archivo"].get("es") == cv["archivo"].get("en"):
        errores.append("cv.archivo.es y cv.archivo.en apuntan al mismo PDF")
    for i, x in enumerate(s["experiencia"]):
        if x.get("tipo") not in (None, "premio"):
            errores.append(f"experiencia[{i}] tiene tipo '{x['tipo']}': el CV solo conoce 'premio' (o sin tipo)")
    if not any(x.get("tipo") is None for x in s["experiencia"]):
        errores.append("No hay entradas de experiencia sin 'tipo: premio' para la sección Experiencia")
    for p in s["proyectos"]:
        for e in p["enlaces"]:
            if not e["url"].startswith(("https://", "http://")):
                errores.append(f"{p['codigo']}: el enlace '{e['url']}' no es una URL completa (https://…)")
    for f in FUENTES:
        if not (RAIZ / "assets/fuentes" / f).exists():
            errores.append(f"No existe la fuente assets/fuentes/{f}")
    return errores


def avisos_cv(s):
    """Diferencias que no impiden generar, pero conviene revisar."""
    return [f"cv.titulo_profesional.{lang} ya no coincide con portada.linea_superior.{lang}; revisa si es a propósito"
            for lang in IDIOMAS
            if s["cv"]["titulo_profesional"][lang].upper() != s["portada"]["linea_superior"][lang].upper()]


def main():
    s = yaml.safe_load((RAIZ / "data/perfil.yml").read_text(encoding="utf-8"))
    errores = validar(s) + validar_cv(s)
    if errores:
        print("No se generó nada. Corrige data/perfil.yml:\n  - " + "\n  - ".join(errores))
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"), autoescape=select_autoescape(["html", "j2"]),
                      undefined=StrictUndefined, trim_blocks=False, lstrip_blocks=False)
    plantilla = env.get_template("cv.html.j2")
    hoy = datetime.date.today()
    trabajos = [x for x in s["experiencia"] if x.get("tipo") is None]
    premios = [x for x in s["experiencia"] if x.get("tipo") == "premio"]
    ancho_util = CARTA[0] - MARGENES["left"] - MARGENES["right"]
    alto_util = CARTA[1] - MARGENES["top"] - MARGENES["bottom"]

    pdfs, problemas = {}, []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        navegador = pw.chromium.launch()
        for lang in IDIOMAS:
            def t(x, lang=lang):
                v = x[lang] if es_traducible(x) else x
                return junto(v) if isinstance(v, str) else v

            def lista(elementos, sep=", ", t=t):
                return sep.join(t(e) for e in elementos)

            portafolio = s["sitio"]["url"] + ("" if lang == "es" else "en/")
            try:
                html = plantilla.render(
                    s=s, lang=lang, t=t, lista=lista, url_visible=url_visible, base=RAIZ.as_uri() + "/",
                    trabajos=trabajos, premios=premios, portafolio=portafolio, ancho_util=ancho_util, alto_util=alto_util,
                    actualizado=f"{t(s['cv']['meses'])[hoy.month - 1]} {hoy.year}",
                )
            except UndefinedError as e:
                problemas.append(f"{lang}: a la plantilla le falta un dato de data/perfil.yml ({e.message})")
                continue
            archivo = pathlib.Path(tmp) / f"cv-{lang}.html"
            archivo.write_text(html, encoding="utf-8")

            # .cv mide exactamente el área útil (ancho_util in), así la medición coincide con la impresión
            pagina = navegador.new_page(viewport={"width": round(CARTA[0] * 96), "height": round(CARTA[1] * 96)})
            pagina.emulate_media(media="print")
            pagina.goto(archivo.as_uri(), wait_until="load")
            fallas = pagina.evaluate(JS_FUENTES)
            if fallas:
                problemas.append(f"{lang}: no cargaron las fuentes {', '.join(fallas)} (revisa assets/fuentes/)")
                continue
            holgura = (alto_util * 96 - pagina.evaluate(JS_ALTO)) * 0.75  # pt libres en la hoja
            pdf = pagina.pdf(format="Letter", print_background=True, tagged=True,
                             margin={lado: f"{v}in" for lado, v in MARGENES.items()})
            paginas = len(re.findall(rb"/Type\s*/Page\b", pdf))
            if paginas != 1 or holgura < 0:
                problemas.append(f"{lang}: no cabe en una página carta ({paginas} páginas; faltan {max(-holgura, 0):.0f} pt). "
                                 "Acorta textos en data/perfil.yml o ajusta plantillas/cv.html.j2")
                continue
            pdfs[lang] = (pdf, holgura)
        navegador.close()

    if problemas:
        print("No se generó nada:\n  - " + "\n  - ".join(problemas))
        sys.exit(1)
    for aviso in avisos_cv(s):
        print(f"Aviso: {aviso}")
    for lang, (pdf, holgura) in pdfs.items():
        destino = RAIZ / s["cv"]["archivo"][lang]
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(pdf)
        print(f"✓ {destino.relative_to(RAIZ)} (1 página · {len(pdf) / 1024:.0f} KB · holgura {holgura:.0f} pt)")


if __name__ == "__main__":
    main()
