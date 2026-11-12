"""Genera el CV en PDF desde data/perfil.yml (fuente única), en el estilo A · Laboratorio.

Uso:
  python3 scripts/generar_cv.py
      Los dos CV públicos del sitio (cv.archivo en data/perfil.yml), uno por idioma.

  python3 scripts/generar_cv.py --postulacion RUTA.yml --salida RUTA.pdf [--idioma es]
      Un CV a la medida de una postulación: agrega «Objetivo» arriba y «En qué puedo aportar» después del
      perfil. No toca los CV públicos. El YAML de la postulación puede vivir fuera del repositorio:
          titulo_profesional: "…"      # opcional; si falta, usa cv.titulo_profesional
          objetivo: "…"
          aportes:
            - {titulo: "…", texto: "…", respaldo: "…"}
          proyectos: ["P-01", "P-02"]  # opcional: qué proyectos mostrar y en qué orden; si falta, los del CV público

Requiere: jinja2, pyyaml, fonttools, brotli y playwright con Chromium (ver scripts/requisitos.txt).
Salida: PDF tamaño carta de una sola página, con texto real y las fuentes incrustadas.

Antes de escribir nada valida la fuente con las mismas reglas del sitio (scripts/generar.py) más las del CV.
Para que la hoja quede bien ocupada prueba el cuerpo del texto de 9.4 a 8.6 pt y elige uno de los más grandes
que caben (el que deja menos filas partidas en dos y menos renglones casi vacíos); el espacio que sobre lo
reparte entre el interlineado y las secciones. Si no cabe ni con 8.6 pt, o si algo más falla, no escribe ningún PDF.
"""
import argparse
import datetime
import pathlib
import re
import sys
import tempfile

import yaml
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.exceptions import UndefinedError
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True  # importar generar.py no debe dejar scripts/__pycache__ en el repo
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generar import IDIOMAS, RAIZ, es_traducible, validar  # noqa: E402  (mismas reglas que el sitio)

# Hoja carta y márgenes, en pulgadas. El pie del CV (una línea pequeña) ocupa el fondo del área útil.
CARTA = (8.5, 11.0)
MARGENES = {"top": 0.44, "right": 0.5, "bottom": 0.3, "left": 0.5}
# Fuentes del sitio. Schibsted Grotesk es variable (400–700): Chromium la incrustaría en el PDF como Type 3
# y sin nombre de peso, así que el CV usa instancias estáticas hechas al vuelo (ver fuentes_estaticas).
FUENTE_SANS, FUENTE_MONO = "schibsted-grotesk.woff2", "fragment-mono-400.woff2"
PESOS = (400, 500, 600, 700)
# Cuerpo del texto, en pt: del más grande al más chico.
CUERPOS = [round(9.4 - 0.1 * i, 1) for i in range(9)]   # 9.4 … 8.6
# Entre los cuerpos que caben se elige, a no más de MARGEN_CUERPO pt del mayor, el que deja la hoja más limpia:
# menos filas partidas en dos renglones (encabezados de entrada, filas de formación, título, contacto; cuentan
# doble) y menos párrafos o viñetas cuyo último renglón ocupa menos de RENGLON_CORTO del ancho.
MARGEN_CUERPO = 0.4
RENGLON_CORTO = 0.2
# Espacio libre al fondo de la hoja, en pt: el mínimo para aceptar un cuerpo y el que se deja al repartir lo demás.
HOLGURA_MIN, HOLGURA_OBJETIVO = 4, 12
# Lo que sobra se reparte primero en interlineado (de la base al tope) y después en aire entre secciones
# (pt por sección: el que se reserva mientras crece el interlineado y el tope).
INTERLINEAS = [1.26, 1.28, 1.3, 1.32, 1.34, 1.36]
AIRE_DESEADO, AIRE_MAX = 2.5, 7
CLAVES_CV = ("archivo", "documento", "titulo_profesional", "perfil", "secciones", "tecnologias", "actualizado", "meses")
SECCIONES_CV = ("objetivo", "perfil", "aportes", "proyectos", "experiencia", "premios", "formacion", "liderazgo", "habilidades")

# Fuerza la carga de todas las fuentes y devuelve las que fallaron (si una falla, Chromium usaría otra sin avisar).
JS_FUENTES = """async () => {
  const caras = [...document.fonts];
  const r = await Promise.allSettled(caras.map(f => f.load()));
  return caras.filter((f, i) => r[i].status !== "fulfilled").map(f => `${f.family} ${f.weight}`);
}"""
# Fija cuerpo, interlineado y aire, y devuelve: el alto natural del contenido en px CSS (sin el alto mínimo
# que empuja el pie al fondo de la hoja), cuántas secciones reciben el aire, cuántas filas de un renglón
# quedaron partidas en dos y cuántos párrafos o viñetas terminan en un renglón casi vacío.
JS_MEDIR = """([cuerpo, interlinea, aire, RENGLON_CORTO]) => {
  const raiz = document.documentElement.style;
  raiz.setProperty("--c", cuerpo + "pt");
  raiz.setProperty("--il", interlinea);
  raiz.setProperty("--aire", aire + "pt");
  const cv = document.querySelector(".cv");
  cv.style.minHeight = "0";
  const alto = cv.getBoundingClientRect().height;
  cv.style.minHeight = "";
  const filas = [...cv.querySelectorAll(".cab__titulo, .cab__contacto, .item__cab h3, .filas li > :first-child, .proy__tec > :first-child")];
  const partidas = filas.filter(e => e.getBoundingClientRect().height > parseFloat(getComputedStyle(e).lineHeight) * 1.5).length;
  // Último renglón de un bloque de texto, como fracción del ancho disponible (1 si el bloque es de un renglón)
  const ultimo = e => {
    const caja = e.getBoundingClientRect(), cs = getComputedStyle(e);
    const izq = parseFloat(cs.paddingLeft), der = parseFloat(cs.paddingRight);
    const alto = caja.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    if (alto < parseFloat(cs.lineHeight) * 1.5) return 1;
    const nodos = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
    let nodo, fin = null;
    while ((nodo = nodos.nextNode())) if (nodo.data.trim()) fin = nodo;
    if (!fin) return 1;
    const largo = fin.data.trimEnd().length, letra = document.createRange();
    letra.setStart(fin, largo - 1);
    letra.setEnd(fin, largo);
    return (letra.getBoundingClientRect().right - caja.left - izq) / (caja.width - izq - der);
  };
  const cortos = [...cv.querySelectorAll("section p:not(.proy__tec):not(.aporte__tit), .puntos li")].filter(e => ultimo(e) < RENGLON_CORTO).length;
  return [alto, cv.querySelectorAll("section").length, partidas, cortos];
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
    if not es_traducible(cv["perfil"]):
        errores.append("cv.perfil (resumen del CV) debe tener «es» y «en»")
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
        if "cv_puntos" in x and not x["cv_puntos"]:
            errores.append(f"experiencia[{i}].cv_puntos está vacío: quítalo o ponle al menos un punto")
    if not any(x.get("tipo") is None for x in s["experiencia"]):
        errores.append("No hay entradas de experiencia sin 'tipo: premio' para la sección Experiencia")
    if not any(p.get("cv", True) for p in s["proyectos"]):
        errores.append("Todos los proyectos tienen «cv: false»: el CV necesita al menos uno")
    for p in s["proyectos"]:
        for e in p["enlaces"]:
            if not e["url"].startswith(("https://", "http://")):
                errores.append(f"{p['codigo']}: el enlace '{e['url']}' no es una URL completa (https://…)")
    for i, f in enumerate(s["perfil"].get("oratoria_comunidad", [])):
        if "cv" in f and not ("programa" in f["cv"] and "fecha" in f["cv"]):
            errores.append(f"perfil.oratoria_comunidad[{i}].cv necesita «programa» y «fecha»")
    for f in (FUENTE_SANS, FUENTE_MONO):
        if not (RAIZ / "assets/fuentes" / f).exists():
            errores.append(f"No existe la fuente assets/fuentes/{f}")
    return errores


def leer_postulacion(ruta, s):
    """Lee el YAML de una postulación. Devuelve (datos, problemas)."""
    try:
        post = yaml.safe_load(pathlib.Path(ruta).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, [f"No se pudo leer la postulación {ruta}: {e}"]
    if not isinstance(post, dict):
        return None, [f"La postulación {ruta} debe ser un YAML con «objetivo» y «aportes»"]
    texto = lambda x: (isinstance(x, str) and x.strip()) or es_traducible(x)
    problemas = []
    if not texto(post.get("objetivo")):
        problemas.append("A la postulación le falta «objetivo» (un texto)")
    aportes = post.get("aportes")
    if not isinstance(aportes, list) or not aportes:
        problemas.append("A la postulación le falta «aportes» (una lista con titulo, texto y respaldo)")
    else:
        for i, a in enumerate(aportes, 1):
            faltan = [c for c in ("titulo", "texto", "respaldo") if not (isinstance(a, dict) and texto(a.get(c)))]
            if faltan:
                problemas.append(f"Al aporte {i} de la postulación le falta: {', '.join(faltan)}")
    if "titulo_profesional" in post and not texto(post["titulo_profesional"]):
        problemas.append("«titulo_profesional» de la postulación está vacío: quítalo o escríbelo")
    if "proyectos" in post:
        codigos = {p["codigo"] for p in s["proyectos"]}
        if not isinstance(post["proyectos"], list) or not post["proyectos"]:
            problemas.append("«proyectos» de la postulación debe ser una lista de códigos, por ejemplo [\"P-01\", \"P-02\"]")
        else:
            problemas += [f"La postulación pide el proyecto {c}, que no existe en data/perfil.yml"
                          for c in post["proyectos"] if c not in codigos]
    return post, problemas


def fuentes_estaticas(carpeta):
    """Una instancia estática de Schibsted Grotesk por peso, en una carpeta temporal.

    Así el PDF lleva cada peso incrustado como TrueType con su nombre (SchibstedGrotesk-Regular, -Medium…)
    en lugar de los trazos Type 3 sin nombre que Chromium genera para una fuente variable.
    """
    rutas = []
    for peso in PESOS:
        fuente = instancer.instantiateVariableFont(TTFont(RAIZ / "assets/fuentes" / FUENTE_SANS), {"wght": peso},
                                                   updateFontNames=True)
        fuente.flavor = None
        destino = pathlib.Path(carpeta) / f"schibsted-grotesk-{peso}.ttf"
        fuente.save(destino)
        rutas.append((peso, destino.as_uri()))
    return {"sans": rutas, "mono": (RAIZ / "assets/fuentes" / FUENTE_MONO).as_uri()}


def holgura_pt(alto_px, alto_util):
    """Puntos libres al fondo de la hoja para un contenido de alto_px (px CSS)."""
    return (alto_util * 96 - alto_px) * 0.75


def ajustar(pagina, alto_util):
    """Elige cuerpo, interlineado y aire entre secciones para que la hoja quede bien ocupada.

    Devuelve (cuerpo, interlinea, aire, holgura) o None si no cabe ni con el cuerpo mínimo. Deja la página
    lista para imprimir con esos valores.
    """
    def medir(cuerpo, interlinea=INTERLINEAS[0], aire=0.0):
        alto, secciones, partidas, cortos = pagina.evaluate(JS_MEDIR, [cuerpo, interlinea, aire, RENGLON_CORTO])
        return holgura_pt(alto, alto_util), secciones, 2 * partidas + cortos

    caben = []   # (cuerpo, holgura, defectos), de mayor a menor cuerpo
    for cuerpo in CUERPOS:
        holgura, secciones, defectos = medir(cuerpo)
        if holgura >= HOLGURA_MIN:
            caben.append((cuerpo, holgura, defectos))
    if not caben:
        return None
    cercanos = [m for m in caben if m[0] >= caben[0][0] - MARGEN_CUERPO - 1e-9]
    cuerpo, holgura, _ = min(cercanos, key=lambda m: (m[2], -m[0]))
    # Interlineado: crece mientras siga quedando el aire deseado entre secciones (no cambia dónde parte cada renglón)
    interlinea = INTERLINEAS[0]
    for il in INTERLINEAS[1:]:
        h, _, _ = medir(cuerpo, il)
        if h < HOLGURA_OBJETIVO + secciones * AIRE_DESEADO:
            break
        interlinea, holgura = il, h
    aire = round(min(max(holgura - HOLGURA_OBJETIVO, 0) / max(secciones, 1), AIRE_MAX), 2)
    holgura, _, _ = medir(cuerpo, interlinea, aire)
    return cuerpo, interlinea, aire, holgura


def componer(navegador, plantilla, s, lang, post, fuentes, carpeta):
    """Arma el CV de un idioma. Devuelve (pdf, resumen) o lanza ValueError con el problema en español."""
    def t(x):
        v = x[lang] if es_traducible(x) else x
        return junto(v) if isinstance(v, str) else v

    def lista(elementos, sep=", "):
        return sep.join(t(e) for e in elementos)

    hoy = datetime.date.today()
    ancho_util = CARTA[0] - MARGENES["left"] - MARGENES["right"]
    alto_util = CARTA[1] - MARGENES["top"] - MARGENES["bottom"]
    portafolio = s["sitio"]["url"] + ("" if lang == "es" else "en/")
    if post and "proyectos" in post:   # la postulación elige proyectos y orden
        por_codigo = {p["codigo"]: p for p in s["proyectos"]}
        proyectos = [por_codigo[c] for c in post["proyectos"]]
    else:
        proyectos = [p for p in s["proyectos"] if p.get("cv", True)]
    try:
        html = plantilla.render(
            s=s, lang=lang, t=t, lista=lista, url_visible=url_visible, fuentes=fuentes, post=post,
            cuerpo=CUERPOS[0], ancho_util=ancho_util, alto_util=alto_util, portafolio=portafolio,
            titulo_profesional=t((post or {}).get("titulo_profesional") or s["cv"]["titulo_profesional"]),
            trabajos=[x for x in s["experiencia"] if x.get("tipo") is None],
            premios=[x for x in s["experiencia"] if x.get("tipo") == "premio"],
            proyectos=proyectos,
            liderazgo=[f for f in s["perfil"].get("oratoria_comunidad", []) if "cv" in f],
            actualizado=f"{t(s['cv']['meses'])[hoy.month - 1]} {hoy.year}",
        )
    except UndefinedError as e:
        raise ValueError(f"a la plantilla le falta un dato de data/perfil.yml ({e.message})") from e
    archivo = pathlib.Path(carpeta) / f"cv-{lang}.html"
    archivo.write_text(html, encoding="utf-8")

    # .cv mide exactamente el área útil (ancho_util in), así la medición coincide con la impresión
    pagina = navegador.new_page(viewport={"width": round(CARTA[0] * 96), "height": round(CARTA[1] * 96)})
    try:
        pagina.emulate_media(media="print")
        pagina.goto(archivo.as_uri(), wait_until="load")
        fallas = pagina.evaluate(JS_FUENTES)
        if fallas:
            raise ValueError(f"no cargaron las fuentes {', '.join(fallas)} (revisa assets/fuentes/)")
        ajuste = ajustar(pagina, alto_util)
        if ajuste is None:
            raise ValueError(f"no cabe en una página carta ni con el cuerpo de {CUERPOS[-1]} pt. Acorta textos en "
                             "data/perfil.yml (cv_puntos, cv_descripcion, cv_fuentes) o en la postulación")
        cuerpo, interlinea, aire, holgura = ajuste
        pdf = pagina.pdf(format="Letter", print_background=True, tagged=True,
                         margin={lado: f"{v}in" for lado, v in MARGENES.items()})
    finally:
        pagina.close()
    paginas = len(re.findall(rb"/Type\s*/Page\b", pdf))
    if paginas != 1:
        raise ValueError(f"el PDF salió de {paginas} páginas aunque la medición decía que cabía; revisa plantillas/cv.html.j2")
    return pdf, (f"1 página · {len(pdf) / 1024:.0f} KB · cuerpo {cuerpo} pt · interlineado {interlinea:g} · "
                 f"aire {aire:g} pt · holgura {holgura:.0f} pt")


def main():
    args = argparse.ArgumentParser(description="Genera el CV en PDF desde data/perfil.yml.")
    args.add_argument("--postulacion", metavar="RUTA.yml", help="YAML con «objetivo» y «aportes» para un CV a la medida")
    args.add_argument("--salida", metavar="RUTA.pdf", help="dónde escribir el CV de la postulación")
    args.add_argument("--idioma", choices=IDIOMAS, default="es", help="idioma del CV de la postulación (por defecto, es)")
    args = args.parse_args()
    if bool(args.postulacion) != bool(args.salida):
        sys.exit("No se generó nada: --postulacion y --salida van juntos.")

    s = yaml.safe_load((RAIZ / "data/perfil.yml").read_text(encoding="utf-8"))
    errores = validar(s) + validar_cv(s)
    post = None
    if args.postulacion:
        post, problemas = leer_postulacion(args.postulacion, s)
        errores += problemas
    if errores:
        print("No se generó nada. Corrige data/perfil.yml o la postulación:\n  - " + "\n  - ".join(errores))
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"), autoescape=select_autoescape(["html", "j2"]),
                      undefined=StrictUndefined, trim_blocks=False, lstrip_blocks=False)
    plantilla = env.get_template("cv.html.j2")
    # Qué se genera: la postulación (un idioma, a --salida) o los CV públicos (todos los idiomas, a cv.archivo)
    destinos = ({args.idioma: pathlib.Path(args.salida).resolve()} if post
                else {lang: RAIZ / s["cv"]["archivo"][lang] for lang in IDIOMAS})

    pdfs, problemas = {}, []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        fuentes = fuentes_estaticas(tmp)
        navegador = pw.chromium.launch()
        for lang in destinos:
            try:
                pdfs[lang] = componer(navegador, plantilla, s, lang, post, fuentes, tmp)
            except ValueError as e:
                problemas.append(f"{lang}: {e}")
        navegador.close()

    if problemas:
        print("No se generó nada:\n  - " + "\n  - ".join(problemas))
        sys.exit(1)
    for lang, (pdf, resumen) in pdfs.items():
        destino = destinos[lang]
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(pdf)
        nombre = destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino
        print(f"✓ {nombre} ({resumen})")


if __name__ == "__main__":
    main()
