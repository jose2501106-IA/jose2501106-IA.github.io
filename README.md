# Portafolio · José Hugo Meza

Sitio: <https://jose2501106-ia.github.io/> (español) · <https://jose2501106-ia.github.io/en/> (inglés)

## Fuente única

Todo el contenido vive en [`data/perfil.yml`](data/perfil.yml). De ese archivo salen el sitio, el CV en PDF y el README del perfil de GitHub (repo `jose2501106-IA`, con `scripts/generar_readme.py`); más adelante, los textos de LinkedIn.

**No edites `index.html`, `en/index.html` ni `404.html` a mano:** se sobrescriben cada vez que se genera el sitio.

## Cómo actualizar

1. Edita `data/perfil.yml`. Cada texto visible va en español (`es`) y en inglés (`en`).
2. Instala las dependencias (solo la primera vez): `pip install -r scripts/requisitos.txt`
3. Genera el sitio: `python3 scripts/generar.py`. Si falta una traducción o una evidencia apunta a un proyecto que no existe, no genera nada y te dice qué corregir.
4. Regenera el CV en PDF: `python3 scripts/generar_cv.py`. Escribe `cv/jose-hugo-meza-cv-es.pdf` y `cv/jose-hugo-meza-cv-en.pdf`, una página carta cada uno. Si algo no cabe en la página o falta un dato, no escribe nada y te dice qué corregir. La primera vez necesita `python3 -m playwright install chromium`.
5. Si cambiaste el título principal o la foto, regenera la vista previa y los íconos: `python3 -m playwright install chromium` y luego `python3 scripts/imagenes.py`.
6. Revisa y sube los cambios.

### Imagen de cada proyecto

Cada tarjeta de proyecto lleva **una** de estas dos cosas (el generador no avanza si falta o si hay las dos):

- `imagen`: captura real, en proporción 2:1, guardada como `assets/img/proyectos/<nombre>-640.webp` y `<nombre>-1280.webp`, con `alt` (qué se ve) y `pie` (qué es: captura, datos ficticios…).
- `esquema`: diagrama hecho con texto de la propia ficha (`pasos` y, si aplica, `versiones`). Sirve para proyectos privados o sin captura pública; no inventa datos: solo usa lo que ya dice la ficha.

Nunca subas una captura con datos reales de clientes, montos, nombres o pantallas privadas.

## Estructura

| Ruta | Qué es |
|---|---|
| `data/perfil.yml` | Contenido (fuente única) |
| `plantillas/` | Plantillas del sitio, del CV y de la imagen para compartir |
| `scripts/` | Generadores del sitio, del CV y de imágenes |
| `cv/` | CV en PDF generado (español e inglés) |
| `reconocimientos/` | Reconocimientos en PDF que enlaza la sección de liderazgo |
| `assets/` | Estilos, JavaScript, fuentes, retrato, logos, imágenes de proyectos e imágenes para compartir |
| `index.html`, `en/index.html` | Páginas generadas |
| `404.html` | Página de «no encontrada», bilingüe (GitHub Pages la muestra en cualquier dirección que no exista) |
| `sitemap.xml`, `robots.txt`, íconos | Para buscadores y navegadores |
