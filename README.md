# Portafolio · José Hugo Meza

Sitio: <https://jose2501106-ia.github.io/> (español) · <https://jose2501106-ia.github.io/en/> (inglés)

## Fuente única

Todo el contenido vive en [`data/perfil.yml`](data/perfil.yml). De ese archivo salen el sitio y, más adelante, el README del perfil, los textos de LinkedIn y el CV.

**No edites `index.html` ni `en/index.html` a mano:** se sobrescriben cada vez que se genera el sitio.

## Cómo actualizar

1. Edita `data/perfil.yml`. Cada texto visible va en español (`es`) y en inglés (`en`).
2. Instala las dependencias (solo la primera vez): `pip install -r scripts/requisitos.txt`
3. Genera el sitio: `python3 scripts/generar.py`. Si falta una traducción o una evidencia apunta a un proyecto que no existe, no genera nada y te dice qué corregir.
4. Si cambiaste el título principal o la foto, regenera la vista previa y los íconos: `python3 -m playwright install chromium` y luego `python3 scripts/imagenes.py`.
5. Revisa y sube los cambios.

## Estructura

| Ruta | Qué es |
|---|---|
| `data/perfil.yml` | Contenido (fuente única) |
| `plantillas/` | Plantilla del sitio y de la imagen para compartir |
| `scripts/` | Generador del sitio y de imágenes |
| `assets/` | Estilos, JavaScript, fuentes, retrato, logos e imágenes para compartir |
| `index.html`, `en/index.html` | Páginas generadas |
| `sitemap.xml`, `robots.txt`, íconos | Para buscadores y navegadores |

Los apuntes y el proyecto Lean Six Sigma que siguen en la raíz se mudan a sus propios repos en la fase 2.
