// Efectos ligeros de la página. Con "reducir movimiento" no se mueve nada y todo queda en su estado final.
(() => {
  const QUIETO = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $$ = (s) => [...document.querySelectorAll(s)];
  const lim = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

  // 1 · Titular palabra a palabra al cargar. Cada palabra conserva la clase de su trozo (cromado o rojo).
  const h1 = document.querySelector("h1");
  if (h1 && !QUIETO) {
    h1.setAttribute("aria-label", h1.textContent.replace(/\s+/g, " ").trim());
    let i = 0;
    const trocea = (nodo, clase) => {
      [...nodo.childNodes].forEach((n) => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach((w) => {
            if (!w) return;
            if (/^\s+$/.test(w)) { frag.append(w); return; }
            const s = document.createElement("span");
            s.className = ("pal " + clase).trim();
            s.style.setProperty("--i", i++);
            s.setAttribute("aria-hidden", "true");
            s.textContent = w;
            frag.append(s);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && n.tagName !== "BR") {
          const c = n.className;
          n.removeAttribute("class");
          trocea(n, c);
        }
      });
    };
    trocea(h1, "");
    h1.classList.add("trocea");
    requestAnimationFrame(() => requestAnimationFrame(() => h1.classList.add("go")));
  }

  // 2 · Cifras que cuentan desde 0 al entrar en pantalla. Se respeta el formato ("−33 %", "+200 mil").
  const fmt = (n) => n.toLocaleString("es-ES");
  function cuenta(el) {
    const fin = el.textContent;
    const m = fin.match(/^(\D*?)([\d.]+)(.*)$/);
    if (!m || QUIETO) return;
    const n = parseInt(m[2].replace(/\./g, ""), 10);
    if (!n) return;
    const t0 = performance.now(), dur = n > 50 ? 1400 : 900;
    // Red de seguridad: si el navegador frena la animación, la cifra acaba igual en su valor.
    const seguro = setTimeout(() => { el.textContent = fin; }, dur + 200);
    (function paso(t) {
      const p = 1 - Math.pow(1 - lim((t - t0) / dur), 3);
      el.textContent = p >= 1 ? fin : m[1] + fmt(Math.round(n * p)) + m[3];
      if (p < 1) requestAnimationFrame(paso); else clearTimeout(seguro);
    })(t0);
  }
  window.cuentaCifras = (els) => {
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { io.unobserve(e.target); cuenta(e.target); }
    }), { threshold: 0.4 });
    els.forEach((el) => io.observe(el));
  };

  // 3 · Banda de palabras que corre con el scroll y se inclina al acelerar. Avanza y retrocede con el dedo.
  const pista = document.querySelector(".cinta .pista");
  if (pista && !QUIETO) {
    let ultimoY = scrollY, vel = 0, corriendo = false;
    const cuadro = () => {
      const y = scrollY;
      vel += (y - ultimoY - vel) * 0.18; ultimoY = y;
      const mitad = pista.scrollWidth / 2, off = (y * 0.45) % mitad;
      const sk = Math.max(-9, Math.min(9, vel * -0.35));
      pista.style.transform = `translate3d(${(-off).toFixed(1)}px,0,0) skewX(${sk.toFixed(2)}deg)`;
      if (Math.abs(vel) > 0.05) requestAnimationFrame(cuadro); else corriendo = false;
    };
    const pide = () => { if (!corriendo) { corriendo = true; requestAnimationFrame(cuadro); } };
    addEventListener("scroll", pide, { passive: true });
    pide();
  }

  // 4 · Chispas al pulsar los botones de comprar y de unirse. Funciona también al tocar con el dedo.
  if (!QUIETO) {
    const cv = document.createElement("canvas");
    cv.className = "chispas";
    cv.setAttribute("aria-hidden", "true");
    document.body.append(cv);
    const ctx = cv.getContext("2d");
    let chispas = [], activo = false;
    const tam = () => {
      const r = Math.min(devicePixelRatio || 1, 2);
      cv.width = innerWidth * r; cv.height = innerHeight * r;
      ctx.setTransform(r, 0, 0, r, 0, 0);
    };
    tam(); addEventListener("resize", tam);
    const pinta = (t) => {
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      chispas = chispas.filter((c) => t - c.t0 < 400);
      chispas.forEach((c) => {
        const p = (t - c.t0) / 400, e = 1 - Math.pow(1 - p, 2);
        const d1 = 8 + e * 22, d2 = d1 + 10 * (1 - p);
        ctx.strokeStyle = c.color; ctx.lineWidth = 2.5; ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(c.x + Math.cos(c.a) * d1, c.y + Math.sin(c.a) * d1);
        ctx.lineTo(c.x + Math.cos(c.a) * d2, c.y + Math.sin(c.a) * d2);
        ctx.stroke();
      });
      if (chispas.length) requestAnimationFrame(pinta); else activo = false;
    };
    document.addEventListener("pointerdown", (e) => {
      const b = e.target.closest(".btn--red, .btn--tg, .btn--fb, .btn--white");
      if (!b) return;
      const t0 = performance.now();
      for (let k = 0; k < 8; k++) chispas.push({ x: e.clientX, y: e.clientY, a: (k / 8) * Math.PI * 2, t0, color: k % 2 ? "#FFD23F" : "#E3262B" });
      if (!activo) { activo = true; requestAnimationFrame(pinta); }
    });
  }
})();
