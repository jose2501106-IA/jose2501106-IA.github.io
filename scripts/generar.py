"""Genera el portafolio desde data/perfil.yml (fuente única).

Uso:  python3 scripts/generar.py
Salida: index.html (español), en/index.html (inglés), sitemap.xml y robots.txt.

Antes de escribir nada valida la fuente: traducciones completas, evidencias que
apuntan a proyectos existentes y logos conocidos. Si algo falla, no genera.
"""
import datetime
import hashlib
import json
import pathlib
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

RAIZ = pathlib.Path(__file__).resolve().parent.parent
IDIOMAS = ("es", "en")
ANCLAS_NAV = ["roles", "proyectos", "experiencia", "perfil", "contacto"]

# Logos: archivo y tamaño en pantalla (px). Son decorativos: el texto de al lado ya nombra la institución.
LOGOS = {
    "medalla-2": ("medalla-2.svg", 37, 52),
    "medalla-3": ("medalla-3.svg", 37, 52),
    "unam": ("unam.webp", 41, 46),
    "hybridge": ("hybridge.svg", 110, 19),
    "uveg": ("uveg.svg", 78, 21),
    "anahuac": ("anahuac.svg", 32, 32),
    "aspire": ("aspire.svg", 80, 28),
    "one": ("one.svg", 62, 32),
    "oracle": ("oracle.svg", 104, 13),
    "lssi": ("lssi.svg", 78, 32),
    "stellar": ("stellar.svg", 96, 24),      # SVG oficial de @stellar/design-system (solo cambian colores)
    "baf": ("baf.webp", 56, 28),             # imagen entregada por José, recortada (sin redibujar)
    "senado": ("senado.webp", 46, 46),                    # imágenes entregadas por José, recortadas (sin redibujar).
    #   El sello del Senado va siempre en sus colores originales (su manual de identidad no permite cambiarle
    #   el color): la capa del modo plano es la misma imagen a color.
    "congreso-oaxaca": ("congreso-oaxaca.webp", 88, 44),
    "wya": ("wya.webp", 50, 48),                           # World Youth Alliance: logo tomado del reconocimiento de José
}


def es_traducible(x):
    return isinstance(x, dict) and "es" in x and "en" in x


def validar(s):
    """Devuelve una lista de problemas; vacía si la fuente está bien."""
    errores = []

    def recorrer(x, ruta):
        if isinstance(x, dict):
            if ("es" in x) != ("en" in x):
                errores.append(f"Falta traducción en {ruta}: tiene {sorted(k for k in x if k in IDIOMAS)}")
            for k, v in x.items():
                recorrer(v, f"{ruta}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                recorrer(v, f"{ruta}[{i}]")
        elif isinstance(x, str) and not x.strip():
            errores.append(f"Texto vacío en {ruta}")

    recorrer(s, "perfil")
    codigos = {p["codigo"] for p in s["proyectos"]}
    for r in s["roles"]:
        for e in r["evidencia"]:
            if e not in codigos:
                errores.append(f"El rol {r['codigo']} cita {e}, que no existe en proyectos")
    for c in s["portada"]["cifras"]:
        if c["codigo"] not in codigos:
            errores.append(f"La cifra '{c['valor']}' cita {c['codigo']}, que no existe en proyectos")
    for p in s["proyectos"]:
        for c in p["categorias"]:
            if c not in s["categorias"]:
                errores.append(f"{p['codigo']} usa la categoría '{c}', que no está definida")
        for d in p.get("distinciones", {}).get("premios", []):
            if d["medalla"] not in LOGOS:
                errores.append(f"{p['codigo']} usa la medalla '{d['medalla']}', que no está en LOGOS")
    for x in s["experiencia"]:
        if x.get("logo") and x["logo"] not in LOGOS:
            errores.append(f"Logo desconocido en experiencia: {x['logo']}")
    for f in s["perfil"]["formacion"] + s["perfil"].get("oratoria_comunidad", []):
        for fa in f.get("fases", []):
            if "nombre" not in fa or "estado" not in fa:
                errores.append(f"Una fase de {f['institucion']} no tiene nombre o estado")
        for l in f.get("logos", []):
            if l not in LOGOS:
                errores.append(f"Logo desconocido en formación: {l}")
    for nombre, (archivo, _, _) in LOGOS.items():
        for carpeta in ("", "color/"):
            if not (RAIZ / "assets/img/logos" / carpeta / archivo).exists():
                errores.append(f"No existe el archivo del logo {nombre}: assets/img/logos/{carpeta}{archivo}")
    return errores


def version_activos():
    h = hashlib.sha256()
    for f in ("assets/css/sitio.css", "assets/js/sitio.js"):
        h.update((RAIZ / f).read_bytes())
    return h.hexdigest()[:8]


def json_ld(s, lang):
    t = lambda x: x[lang] if es_traducible(x) else x
    datos = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": s["sitio"]["nombre_completo"],
        "alternateName": s["sitio"]["nombre"],
        "url": s["sitio"]["url"],
        "image": s["sitio"]["url"] + "assets/img/retrato-864.webp",
        "jobTitle": "Desarrollador de IA y automatización" if lang == "es" else "AI and automation developer",
        "description": t(s["sitio"]["descripcion"]),
        "email": "mailto:" + s["contacto"]["correo"],
        "address": {"@type": "PostalAddress", "addressLocality": "Ciudad de México", "addressCountry": "MX"},
        "sameAs": [s["contacto"]["linkedin_url"], s["contacto"]["github_url"]],
        "knowsLanguage": ["es", "en"],
    }
    return Markup(json.dumps(datos, ensure_ascii=False).replace("</", "<\\/"))


def main():
    s = yaml.safe_load((RAIZ / "data/perfil.yml").read_text(encoding="utf-8"))
    errores = validar(s)
    if "cv" in s:  # el sitio enlaza al CV: los PDF deben existir antes de publicar
        for lang in IDIOMAS:
            if not (RAIZ / s["cv"]["archivo"][lang]).exists():
                errores.append(f"Falta el CV {s['cv']['archivo'][lang]}: genéralo con python3 scripts/generar_cv.py")
    if errores:
        print("No se generó nada. Corrige data/perfil.yml:\n  - " + "\n  - ".join(errores))
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"), autoescape=select_autoescape(["html", "j2"]),
                      undefined=StrictUndefined, trim_blocks=False, lstrip_blocks=False)
    plantilla = env.get_template("pagina.html.j2")
    version = version_activos()
    conteo = {c: sum(c in p["categorias"] for p in s["proyectos"]) for c in s["categorias"]}

    for lang in IDIOMAS:
        raiz = "" if lang == "es" else "../"

        def t(x, lang=lang):
            return x[lang] if es_traducible(x) else x

        def logo(clave, raiz=raiz):
            # Dos capas, como el componente original del diseño: contorno azul (modo plano) y color de marca.
            # El CSS cruza de una a otra al pasar el cursor por su fila o caja, o con el modo plano apagado.
            archivo, ancho, alto = LOGOS[clave]
            capa = lambda carpeta, clase: (f'<img class="{clase}" src="{raiz}assets/img/logos/{carpeta}{archivo}" '
                                           f'width="{ancho}" height="{alto}" alt="" loading="lazy" decoding="async">')
            return Markup(f'<span class="logo">{capa("", "logo__linea")}{capa("color/", "logo__color")}</span>')

        html = plantilla.render(
            s=s, lang=lang, raiz=raiz, t=t, logo=logo, version=version, conteo=conteo,
            nav=list(zip(t(s["ui"]["nav"]), ANCLAS_NAV)),
            url_pagina=s["sitio"]["url"] + ("" if lang == "es" else "en/"),
            jsonld=json_ld(s, lang),
        )
        destino = RAIZ / ("index.html" if lang == "es" else "en/index.html")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        print(f"✓ {destino.relative_to(RAIZ)} ({len(html.encode()):,} bytes)")

    hoy = datetime.date.today().isoformat()
    url = s["sitio"]["url"]
    alternas = f'<xhtml:link rel="alternate" hreflang="es" href="{url}"/><xhtml:link rel="alternate" hreflang="en" href="{url}en/"/>'
    (RAIZ / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"  <url><loc>{url}</loc>{alternas}<lastmod>{hoy}</lastmod></url>\n"
        f"  <url><loc>{url}en/</loc>{alternas}<lastmod>{hoy}</lastmod></url>\n"
        "</urlset>\n", encoding="utf-8")
    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}sitemap.xml\n", encoding="utf-8")
    print("✓ sitemap.xml · robots.txt")


if __name__ == "__main__":
    main()
