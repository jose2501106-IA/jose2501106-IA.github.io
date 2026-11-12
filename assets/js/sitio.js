/* Portafolio · interacción mínima: menú de celular, filtros de proyectos, sección actual en el menú
   y barra de acciones del celular. Sin dependencias.
   Si este archivo no carga, el sitio se ve y se lee completo (sin barra ni filtros activos). */
(() => {
  const d = document;
  const root = d.documentElement;

  // Menú de celular y tableta
  const btnMenu = d.querySelector(".nav__menu");
  const enlaces = d.getElementById("nav-enlaces");
  const cerrarMenu = () => { btnMenu?.setAttribute("aria-expanded", "false"); enlaces?.classList.remove("abierto"); };
  btnMenu?.addEventListener("click", () => {
    const abrir = btnMenu.getAttribute("aria-expanded") !== "true";
    btnMenu.setAttribute("aria-expanded", String(abrir));
    enlaces.classList.toggle("abierto", abrir);
  });
  enlaces?.addEventListener("click", (e) => { if (e.target.closest("a")) cerrarMenu(); });
  d.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && btnMenu?.getAttribute("aria-expanded") === "true") { cerrarMenu(); btnMenu.focus(); }
  });
  d.addEventListener("click", (e) => { if (!e.target.closest(".cabecera")) cerrarMenu(); });
  // Si el foco del teclado sale de la cabecera, el menú se cierra (no tapa lo que sigue)
  d.addEventListener("focusin", (e) => { if (!e.target.closest(".cabecera")) cerrarMenu(); });
  matchMedia("(min-width: 1080px)").addEventListener?.("change", cerrarMenu);

  // Filtros de proyectos
  const botones = d.querySelectorAll("[data-filtro]");
  const tarjetas = d.querySelectorAll("[data-cat]");
  const filtrar = (f) => {
    botones.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.filtro === f)));
    tarjetas.forEach((t) => { t.hidden = !(f === "todos" || t.dataset.cat.split(" ").includes(f)); });
  };
  botones.forEach((b) => b.addEventListener("click", () => filtrar(b.dataset.filtro)));
  // Un enlace de evidencia nunca debe llevar a una ficha escondida por un filtro
  d.querySelectorAll('a[href^="#p-"]').forEach((a) => a.addEventListener("click", () => {
    const t = d.querySelector(a.getAttribute("href"));
    if (t && t.hidden) filtrar("todos");
  }));

  // Al leer: el menú marca la sección en pantalla (aria-current), el cambio de idioma conserva la sección
  // y, en celular, la barra de acciones aparece después de los botones de la portada y se va en Contacto.
  const secciones = [...d.querySelectorAll("main > section[id]")];
  const navPorSeccion = new Map([...d.querySelectorAll('#nav-enlaces a[href^="#"]')].map((a) => [a.hash.slice(1), a]));
  const otroIdioma = d.querySelector('.idioma a:not([aria-current])');
  const baseOtroIdioma = otroIdioma?.getAttribute("href");
  const barra = d.querySelector(".barra");
  const botonesPortada = d.querySelector(".portada .acciones");
  const contacto = d.getElementById("contacto");
  if (barra) barra.hidden = false;
  let actual, pendiente = 0;
  const revisar = () => {
    pendiente = 0;
    const linea = innerHeight * 0.4;
    let id = null;
    for (const s of secciones) if (s.getBoundingClientRect().top <= linea) id = s.id;
    if (secciones.length && innerHeight + scrollY >= root.scrollHeight - 4) id = secciones[secciones.length - 1].id;   // al final de la página
    if (id !== actual) {
      actual = id;
      navPorSeccion.forEach((a, clave) => (clave === id ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current")));
      if (otroIdioma) otroIdioma.setAttribute("href", baseOtroIdioma + (id && id !== "inicio" ? "#" + id : ""));
    }
    if (barra && botonesPortada && contacto) {
      const visible = botonesPortada.getBoundingClientRect().bottom < 0 && contacto.getBoundingClientRect().top > innerHeight - 40;
      barra.classList.toggle("visible", visible);
    }
  };
  const programar = () => { if (!pendiente) pendiente = requestAnimationFrame(revisar); };
  addEventListener("scroll", programar, { passive: true });
  addEventListener("resize", programar, { passive: true });
  revisar();
})();
