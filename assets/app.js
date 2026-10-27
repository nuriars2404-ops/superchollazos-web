(() => {
  let DATA = window.CHOLLOS || { deals: [], updated: null };
  const CONFIG = window.CONFIG;
  const PAGE = 24;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  const state = { q: "", cat: "Todos", sort: "recent", max: null, minDisc: null, shown: PAGE };

  const euro = (n) => n == null ? "" : n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function ago(iso) {
    const min = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
    if (min < 1) return "ahora mismo";
    if (min < 60) return `hace ${min} min`;
    const h = Math.round(min / 60);
    if (h < 24) return `hace ${h} h`;
    const d = Math.round(h / 24);
    return d === 1 ? "ayer" : `hace ${d} días`;
  }

  // "Marca - Producto, detalles | más detalles" → "Marca - Producto"
  function shortName(title) {
    const head = title.split(/\s[|–]\s|,|\|/)[0].trim();
    return head.split(/\s+/).slice(0, 8).join(" ");
  }

  function storeUrl(store, query) {
    return store.url
      .replace("{q}", encodeURIComponent(query))
      .replace("{dash}", encodeURIComponent(norm(query).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")))
      .replace("{tag}", CONFIG.amazonTag);
  }

  function storeLinks(query) {
    return CONFIG.stores.map((s) => `
      <a class="store" href="${esc(storeUrl(s, query))}" target="_blank" rel="noopener sponsored">
        <span class="store__dot" style="--c:${s.color}">${esc(s.name[0])}</span>
        <span class="store__name">${esc(s.name)}<small>${esc(s.note || "Ver precio")}</small></span>
        <span class="store__go" aria-hidden="true"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg></span>
      </a>`).join("");
  }

  const index = (list) => list.map((d) => ({ ...d, _t: norm(`${d.title} ${d.category}`) }));
  let deals = index(DATA.deals);
  const priceOf = (d) => d.price ?? Infinity;

  function filtered() {
    const words = norm(state.q).split(/\s+/).filter(Boolean);
    let list = deals.filter((d) =>
      (state.cat === "Todos" || d.category === state.cat) &&
      (state.max == null || priceOf(d) <= state.max) &&
      (state.minDisc == null || (d.discount ?? 0) >= state.minDisc) &&
      words.every((w) => d._t.includes(w)));
    if (state.sort === "discount") list = [...list].sort((a, b) => (b.discount ?? 0) - (a.discount ?? 0));
    if (state.sort === "price") list = [...list].sort((a, b) => priceOf(a) - priceOf(b));
    return list;
  }

  function card(d) {
    return `
      <article class="card" data-id="${d.id}">
        <button class="card__media" type="button" data-compare="${d.id}" aria-label="Comparar precio de ${esc(shortName(d.title))}">
          ${d.image ? `<img src="${esc(d.image)}" alt="" loading="lazy" decoding="async">` : `<span class="card__noimg">🔥</span>`}
        </button>
        <div class="card__body">
          <p class="card__meta"><span>${esc(d.category)}</span><span>${ago(d.date)}</span></p>
          <h3 class="card__title" title="${esc(d.title)}">${esc(d.title)}</h3>
          <p class="price">
            <strong>${euro(d.price)}</strong>
            ${d.oldPrice ? `<s>${euro(d.oldPrice)}</s>` : ""}
            ${d.discount ? `<span class="pill pill--red">−${d.discount}%</span>` : ""}
          </p>
          <div class="card__actions">
            <a class="btn btn--red btn--sm" href="${esc(d.link)}" target="_blank" rel="noopener sponsored">Ver en ${esc(d.store)}</a>
            <button class="btn btn--outline btn--sm" type="button" data-compare="${d.id}">Comparar</button>
          </div>
        </div>
      </article>`;
  }

  function render() {
    const list = filtered();
    $("[data-grid]").innerHTML = list.slice(0, state.shown).map(card).join("");
    $("[data-empty]").hidden = list.length > 0;
    $("[data-more]").hidden = list.length <= state.shown;

    const title = state.q ? `${list.length} ${list.length === 1 ? "chollo" : "chollos"} para «${esc(state.q)}»`
      : state.cat !== "Todos" ? esc(state.cat) : "Últimos chollos";
    $("[data-results-title]").innerHTML = title;

    const strip = $("[data-compare-strip]");
    strip.hidden = !state.q;
    if (state.q) {
      $("[data-compare-q]").textContent = state.q;
      $("[data-store-links]").innerHTML = storeLinks(state.q);
    }
  }

  function renderCats() {
    const counts = deals.reduce((m, d) => (m[d.category] = (m[d.category] || 0) + 1, m), {});
    const cats = ["Todos", ...Object.keys(counts).sort((a, b) => counts[b] - counts[a])];
    $("[data-cats]").innerHTML = cats.map((c) =>
      `<button type="button" role="tab" data-cat="${esc(c)}" aria-selected="${c === state.cat}">${esc(c)}${c !== "Todos" ? ` <small>${counts[c]}</small>` : ""}</button>`).join("");
  }

  function renderHero() {
    const dayAgo = Date.now() - 864e5;
    const today = deals.filter((d) => new Date(d.date) > dayAgo);
    const pool = today.length ? today : deals;
    const withDisc = pool.filter((d) => d.discount);
    $("[data-stat=today]").textContent = today.length;
    $("[data-stat=avg]").textContent = withDisc.length ? `−${Math.round(withDisc.reduce((s, d) => s + d.discount, 0) / withDisc.length)} %` : "–";
    $("[data-stat=cheap]").textContent = pool.filter((d) => priceOf(d) < 20).length;
    if (DATA.updated) $("[data-fresh]").textContent = `Actualizado ${ago(DATA.updated)}`;

    // Chollo del día: el mayor descuento de las últimas 24 h, con foto.
    const top = [...pool].filter((d) => d.image).sort((a, b) => (b.discount ?? 0) - (a.discount ?? 0))[0];
    if (!top) return;
    $("[data-featured]").innerHTML = `
      <p class="featured__tag"><b>#1</b> Chollo del día</p>
      <button class="featured__media" type="button" data-compare="${top.id}" aria-label="Comparar precio">
        <img src="${esc(top.image)}" alt="">
      </button>
      <h2 class="featured__title">${esc(shortName(top.title))}</h2>
      <p class="price price--lg"><strong>${euro(top.price)}</strong>${top.oldPrice ? `<s>${euro(top.oldPrice)}</s>` : ""}</p>
      <div class="card__actions">
        <a class="btn btn--red" href="${esc(top.link)}" target="_blank" rel="noopener sponsored">¡Lo quiero!</a>
        <button class="btn btn--outline" type="button" data-compare="${top.id}">Comparar precio</button>
      </div>`;
  }

  function openCompare(id) {
    const d = deals.find((x) => x.id === id);
    if (!d) return;
    const q = shortName(d.title);
    // Veces que el mismo producto ha salido en el canal, para ver si ahora está más barato.
    const history = d.asin ? deals.filter((x) => x.asin === d.asin).sort((a, b) => new Date(b.date) - new Date(a.date)) : [d];
    const lowest = Math.min(...history.map(priceOf));
    const similar = deals.filter((x) => x.id !== d.id && x.category === d.category && x.asin !== d.asin)
      .map((x) => ({ x, score: norm(q).split(/\s+/).filter((w) => w.length > 3 && x._t.includes(w)).length }))
      .filter((s) => s.score > 0).sort((a, b) => b.score - a.score || priceOf(a.x) - priceOf(b.x)).slice(0, 4);

    $("[data-modal-body]").innerHTML = `
      <button class="modal__close" type="button" data-close aria-label="Cerrar" autofocus>×</button>
      <div class="cmp">
        <div class="cmp__product">
          ${d.image ? `<img src="${esc(d.image)}" alt="">` : ""}
          <div>
            <p class="card__meta"><span>${esc(d.category)}</span><span>${ago(d.date)}</span></p>
            <h2 id="modal-title">${esc(d.title)}</h2>
            <p class="price price--lg"><strong>${euro(d.price)}</strong>${d.oldPrice ? `<s>${euro(d.oldPrice)}</s>` : ""}${d.discount ? `<span class="pill">−${d.discount}%</span>` : ""}</p>
            ${d.oldLabel && d.oldPrice ? `<p class="muted">Precio tachado: ${esc(d.oldLabel.toLowerCase())}.</p>` : ""}
            <a class="btn btn--red" href="${esc(d.link)}" target="_blank" rel="noopener sponsored">Comprar en ${esc(d.store)} por ${euro(d.price)}</a>
          </div>
        </div>

        ${history.length > 1 ? `
        <section class="cmp__sec">
          <h3>Veces que lo hemos publicado</h3>
          <ul class="hist">${history.map((h) => `<li><span>${new Date(h.date).toLocaleString("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span><strong>${euro(h.price)}</strong>${h.price === lowest ? `<em>más barato</em>` : ""}</li>`).join("")}</ul>
        </section>` : ""}

        ${d.asin && d.store === "Amazon" ? `
        <section class="cmp__sec">
          <h3>Historial de precio en Amazon</h3>
          <a class="chart" href="https://es.camelcamelcamel.com/product/${esc(d.asin)}" target="_blank" rel="noopener">
            <img src="https://charts.camelcamelcamel.com/es/${esc(d.asin)}/amazon.png?force=1&zero=0&w=720&h=300&tp=3m&lang=es_ES" alt="Gráfica del precio en Amazon en los últimos 90 días" loading="lazy" onerror="this.closest('.cmp__sec').remove()">
          </a>
          <p class="muted">Últimos 3 meses, datos de CamelCamelCamel. Si la línea está en su punto más bajo, es buen momento para comprar.</p>
        </section>` : ""}

        <section class="cmp__sec">
          <h3>Búscalo en otras tiendas</h3>
          <p class="muted">Buscamos «${esc(q)}». Si lo encuentras por menos de ${euro(d.price)}, ¡adelante!</p>
          <div class="stores stores--modal">${storeLinks(q)}</div>
        </section>

        ${similar.length ? `
        <section class="cmp__sec">
          <h3>Parecidos en el canal</h3>
          <div class="mini">${similar.map(({ x }) => `
            <button type="button" class="mini__item" data-compare="${x.id}">
              ${x.image ? `<img src="${esc(x.image)}" alt="" loading="lazy">` : ""}
              <span>${esc(shortName(x.title))}</span>
              <strong>${euro(x.price)}</strong>
            </button>`).join("")}</div>
        </section>` : ""}
      </div>`;
    const modal = $("[data-modal]");
    if (!modal.open) modal.showModal();
    requestAnimationFrame(() => { $(".modal__body", modal).scrollTop = 0; });
  }

  // Eventos
  function setQuery(q) {
    state.q = q.trim();
    state.shown = PAGE;
    $$("[data-search] input").forEach((i) => { if (i.value !== q) i.value = q; });
    render();
  }

  let t;
  $$("[data-search]").forEach((form) => {
    const input = $("input", form);
    input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => setQuery(input.value), 180); });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      setQuery(input.value);
      (state.q ? $("[data-compare-strip]") : $("#chollos")).scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-q],[data-cat],[data-max],[data-min-disc],[data-compare],[data-more],[data-close]");
    if (!el) return;
    if (el.dataset.q) {
      setQuery(el.dataset.q);
      $("[data-compare-strip]").scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (el.dataset.cat) {
      state.cat = el.dataset.cat; state.shown = PAGE;
      $$("[data-cat]").forEach((b) => b.setAttribute("aria-selected", b === el));
      render();
    } else if (el.dataset.max || el.dataset.minDisc) {
      const key = el.dataset.max ? "max" : "minDisc";
      const val = Number(el.dataset.max || el.dataset.minDisc);
      state[key] = state[key] === val ? null : val;
      if (key === "max") $$("[data-max]").forEach((b) => b.setAttribute("aria-pressed", Number(b.dataset.max) === state.max));
      else el.setAttribute("aria-pressed", state.minDisc != null);
      state.shown = PAGE;
      render();
    } else if (el.dataset.compare) {
      openCompare(Number(el.dataset.compare));
    } else if (el.hasAttribute("data-more")) {
      state.shown += PAGE; render();
    } else if (el.hasAttribute("data-close")) {
      $("[data-modal]").close();
    }
  });

  $("[data-modal]").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });
  $("[data-sort]").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  $("[data-year]").textContent = new Date().getFullYear();

  const initial = new URLSearchParams(location.search).get("q");
  renderCats();
  renderHero();
  if (initial) setQuery(initial); else render();

  // Mientras la página está abierta, mira cada 2 minutos si el servidor tiene chollos nuevos.
  async function refresh() {
    if (document.hidden || $("[data-modal]").open) return;
    try {
      const res = await fetch(`data/deals.js?t=${Date.now()}`, { cache: "no-store" });
      const text = await res.text();
      const next = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
      if (next.updated === DATA.updated) return;
      const known = new Set(deals.map((d) => d.id));
      const fresh = next.deals.filter((d) => !known.has(d.id)).length;
      DATA = next;
      deals = index(next.deals);
      renderCats();
      renderHero();
      render();
      if (fresh) toast(`🔥 ${fresh} ${fresh === 1 ? "chollo nuevo" : "chollos nuevos"}`);
    } catch { /* sin conexión: se reintenta en la siguiente vuelta */ }
  }

  function toast(text) {
    const el = document.createElement("button");
    el.className = "toast";
    el.type = "button";
    el.textContent = text;
    el.addEventListener("click", () => { $("#chollos").scrollIntoView({ behavior: "smooth" }); el.remove(); });
    document.body.append(el);
    setTimeout(() => el.remove(), 8000);
  }

  setInterval(refresh, 120000);
  document.addEventListener("visibilitychange", refresh);
  setInterval(() => { if (DATA.updated) $("[data-fresh]").textContent = `Actualizado ${ago(DATA.updated)}`; }, 60000);
})();
