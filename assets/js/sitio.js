/* Portafolio · interacción mínima: menú de celular, filtros de proyectos y modo plano.
   Sin dependencias. Si este archivo no carga, el sitio se ve y se lee completo. */
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

  // Modo plano: cruz con coordenadas que sigue al mouse (no aplica en pantallas táctiles)
  const btnPlano = d.querySelector(".btn-plano");
  const listo = () => requestAnimationFrame(() => root.classList.add("listo"));
  if (!btnPlano || !matchMedia("(hover: hover) and (pointer: fine)").matches) {
    root.classList.remove("plano-on");   // sin cursor no hay modo plano: los logos se ven a color
    listo();
    return;
  }
  btnPlano.hidden = false;
  let on = true;
  try { on = localStorage.getItem("plano") !== "off"; } catch (e) { /* almacenamiento no disponible */ }
  const capa = d.createElement("div");
  capa.className = "plano";
  capa.setAttribute("aria-hidden", "true");
  capa.innerHTML = '<div class="plano__celda"></div><div class="plano__v"></div><div class="plano__h"></div><div class="plano__xy"></div>';
  d.body.appendChild(capa);
  const [celda, v, h, xy] = capa.children;
  const aplicar = () => {
    root.classList.toggle("plano-on", on);
    btnPlano.setAttribute("aria-pressed", String(on));
    btnPlano.querySelector("span").textContent = on ? "ON" : "OFF";
  };
  btnPlano.addEventListener("click", () => {
    on = !on;
    try { localStorage.setItem("plano", on ? "on" : "off"); } catch (e) { /* sin persistencia */ }
    aplicar();
  });
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
    if (!on || e.pointerType !== "mouse") return;
    px = e.clientX; py = e.clientY;
    if (!cuadro) cuadro = requestAnimationFrame(pintar);
  }, { passive: true });
  d.addEventListener("mouseleave", () => capa.classList.remove("activo"));
})();
