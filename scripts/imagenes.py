"""Genera las imágenes del sitio que dependen del texto: vista previa para compartir (ES/EN) e íconos.

Uso:  python3 scripts/imagenes.py
Requiere: playwright (con Chromium), jinja2, pyyaml, fonttools, brotli, pillow  (ver scripts/requisitos.txt)
Salida: assets/img/og-es.jpg, assets/img/og-en.jpg, favicon.svg, favicon-32.png, favicon.ico, apple-touch-icon.png
"""
import asyncio
import pathlib
import tempfile

import yaml
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from playwright.async_api import async_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def favicon_svg():
    """Monograma JHM en Space Mono Bold convertido a trazos (no depende de fuentes instaladas)."""
    fuente = TTFont(RAIZ / "assets/fuentes/space-mono-700.woff2")
    glifos, cmap, upm = fuente.getGlyphSet(), fuente.getBestCmap(), fuente["head"].unitsPerEm
    alto_mayus = fuente["OS/2"].sCapHeight or 700
    texto, lado = "JHM", 64
    ancho_unidades = sum(glifos[cmap[ord(c)]].width for c in texto)
    escala = 54 / ancho_unidades
    x = (lado - ancho_unidades * escala) / 2
    base = lado / 2 + alto_mayus * escala / 2
    pluma = SVGPathPen(glifos)
    for c in texto:
        g = glifos[cmap[ord(c)]]
        g.draw(TransformPen(pluma, (escala, 0, 0, -escala, x, base)))
        x += g.width * escala
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}">'
            f'<rect width="{lado}" height="{lado}" fill="#0046B8"/>'
            f'<path fill="#fff" d="{pluma.getCommands()}"/></svg>\n')


async def main():
    s = yaml.safe_load((RAIZ / "data/perfil.yml").read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"), autoescape=True)
    og = env.get_template("og.html.j2")
    svg = favicon_svg()
    (RAIZ / "favicon.svg").write_text(svg, encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        async with async_playwright() as p:
            navegador = await p.chromium.launch()
            # Vista previa para compartir, una por idioma
            for lang in ("es", "en"):
                t = lambda x: x[lang] if isinstance(x, dict) and "es" in x else x
                html = og.render(lang=lang, base=RAIZ.as_uri() + "/", anio=s["sitio"]["anio"],
                                 hoja=t(s["ui"]["hoja"]), perfil=("PERFIL" if lang == "es" else "PROFILE"),
                                 kicker=t(s["portada"]["linea_superior"]), nombre=s["sitio"]["nombre_h1"],
                                 sub=t(s["portada"]["subtitulo"]), bajada=t(s["portada"]["bajada"]),
                                 ruta=("" if lang == "es" else "/en"), idiomas="ES · EN",
                                 escala=t(s["ui"]["escala"]), pie_izq=t(s["portada"]["retrato"]["pie_izq"]))
                archivo = tmp / f"og-{lang}.html"
                archivo.write_text(html, encoding="utf-8")
                pagina = await navegador.new_page(viewport={"width": 1200, "height": 630})
                await pagina.goto(archivo.as_uri(), wait_until="load")
                await pagina.evaluate("document.fonts.ready")
                await pagina.wait_for_timeout(300)
                png = tmp / f"og-{lang}.png"
                await pagina.screenshot(path=str(png))
                destino = RAIZ / f"assets/img/og-{lang}.jpg"
                Image.open(png).convert("RGB").save(destino, "JPEG", quality=86, optimize=True, progressive=True)
                print(f"✓ {destino.relative_to(RAIZ)} ({destino.stat().st_size:,} bytes)")
            # Íconos a partir del SVG
            (tmp / "ico.svg").write_text(svg, encoding="utf-8")
            for nombre, lado in (("favicon-32.png", 32), ("apple-touch-icon.png", 180), ("ico-48.png", 48), ("ico-16.png", 16)):
                pagina = await navegador.new_page(viewport={"width": lado, "height": lado})
                await pagina.goto((tmp / "ico.svg").as_uri())
                ruta = (RAIZ / nombre) if not nombre.startswith("ico-") else (tmp / nombre)
                await pagina.screenshot(path=str(ruta))
            await navegador.close()
        Image.open(tmp / "ico-48.png").save(RAIZ / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("✓ favicon.svg · favicon-32.png · favicon.ico · apple-touch-icon.png")


if __name__ == "__main__":
    asyncio.run(main())
