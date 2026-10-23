/* Portafolio · interacción mínima: menú de celular, filtros de proyectos, sección actual en el menú,
   barra de acciones del celular y vista plano. Sin dependencias.
   Si este archivo no carga, el sitio se ve y se lee completo (sin barra ni vista plano). */
(() => {
  const d = document;
  const root = d.documentElement;

  // Menú de celular
  const btnMenu = d.querySelector(".nav__menu");
  const enlaces = d.getElementById("nav-enlaces");
  const cerrarMenu = () => { btnMenu?.setAttribute("aria-expanded", "false"); enlaces?.classList.remove("abierto"); };
  btnMenu?.addEventListener("click", () => {
    const abrir = btnMenu.getAttribute("aria-expanded") !== "true";
    btnMenu.setAttribute("aria-expanded", String(abrir));
    enlaces.classList.toggle("abierto", abrir);
  });
  enlaces?.addEventListener("click", (e) => { if (e.target.closest("a")) cerrarMenu(); });
  d.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarMenu(); });

  // Filtros de proyectos
  const botones = d.querySelectorAll("[data-filtro]");
  const tarjetas = d.querySelectorAll("[data-cat]");
  const filtrar = (f) => {
    botones.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.filtro === f)));
    tarjetas.forEach((t) => { t.hidden = !(f === "todos" || t.dataset.cat.split(" ").includes(f)); });
  };
  botones.forEach((b) => b.addEventListener("click", () => filtrar(b.dataset.filtro)));
  // Un enlace de evidencia (P-0X) nunca debe llevar a una tarjeta escondida por un filtro
  d.querySelectorAll('a[href^="#p-"]').forEach((a) => a.addEventListener("click", () => {
    const t = d.querySelector(a.getAttribute("href"));
    if (t && t.hidden) filtrar("todos");
  }));

  // Al leer: el menú marca la sección en pantalla (aria-current), el cambio de idioma conserva la sección
  // y, en celular, la barra de acciones aparece después de los botones de la portada y se va en Contacto.
  const secciones = [...d.querySelectorAll("main section[id]")];
  const navPorSeccion = new Map([...d.querySelectorAll('#nav-enlaces a[href^="#"]')].map((a) => [a.hash.slice(1), a]));
  const otroIdioma = d.querySelector('.idioma a:not([aria-current])');
  const baseOtroIdioma = otroIdioma?.getAttribute("href");
  const barra = d.querySelector(".barra");
  const botonesPortada = d.querySelector(".inicio .botones");
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

  // Vista plano: cruz con coordenadas que sigue al mouse y logos en trazo azul.
  // Apagada por defecto; se recuerda solo si quien visita la enciende. Solo con mouse y desde 1024 px
  // (ahí se ve el botón): en pantallas táctiles o angostas no se aplica aunque haya quedado encendida.
  const btnPlano = d.querySelector(".btn-plano");
  const listo = () => requestAnimationFrame(() => root.classList.add("listo"));
  if (!btnPlano || !matchMedia("(hover: hover) and (pointer: fine)").matches) { listo(); return; }
  const ancho = matchMedia("(min-width: 1024px)");
  btnPlano.hidden = false;
  let on = false;
  try { on = localStorage.getItem("plano") === "on"; } catch (e) { /* almacenamiento no disponible */ }
  const capa = d.createElement("div");
  capa.className = "plano";
  capa.setAttribute("aria-hidden", "true");
  capa.innerHTML = '<div class="plano__celda"></div><div class="plano__v"></div><div class="plano__h"></div><div class="plano__xy"></div>';
  d.body.appendChild(capa);
  const [celda, v, h, xy] = capa.children;
  const estado = btnPlano.querySelector(".btn-plano__estado");
  const aplicar = () => {
    const activa = on && ancho.matches;
    root.classList.toggle("plano-on", activa);
    btnPlano.setAttribute("aria-pressed", String(on));
    if (estado) estado.textContent = on ? "ON" : "OFF";
    if (!activa) capa.classList.remove("activo");
  };
  btnPlano.addEventListener("click", () => {
    on = !on;
    try { localStorage.setItem("plano", on ? "on" : "off"); } catch (e) { /* sin persistencia */ }
    aplicar();
  });
  ancho.addEventListener?.("change", aplicar);
  aplicar();
  listo();
  let px = 0, py = 0, cuadro = 0;
  const pintar = () => {
    cuadro = 0;
    v.style.transform = `translateX(${px}px)`;
    h.style.transform = `translateY(${py}px)`;
    celda.style.transform = `translate(${Math.floor(px / 100) * 100}px, ${Math.floor(py / 100) * 100}px)`;
    const ancho = xy.offsetWidth || 120;
    xy.style.transform = `translate(${Math.min(px + 12, innerWidth - ancho - 4)}px, ${py + 12}px)`;
    xy.textContent = `X ${String(Math.round(px)).padStart(4, "0")} · Y ${String(Math.round(py)).padStart(4, "0")}`;
    capa.classList.add("activo");
  };
  addEventListener("pointermove", (e) => {
    if (!on || !ancho.matches || e.pointerType !== "mouse") return;
    px = e.clientX; py = e.clientY;
    if (!cuadro) cuadro = requestAnimationFrame(pintar);
  }, { passive: true });
  d.addEventListener("mouseleave", () => capa.classList.remove("activo"));
})();
