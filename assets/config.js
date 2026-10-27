// Ajustes de la web. Cambia aquí tus códigos de afiliado.
window.CONFIG = {
  // Es la etiqueta que llevan los enlaces del canal; cámbiala si usas otra.
  amazonTag: "doradita-21",

  // Tiendas del comparador. {q} se sustituye por la búsqueda.
  stores: [
    { name: "Amazon", color: "#FF9900", url: "https://www.amazon.es/s?k={q}&tag={tag}" },
    { name: "AliExpress", color: "#E62E04", url: "https://es.aliexpress.com/w/wholesale-{dash}.html" },
    { name: "Temu", color: "#FB7701", url: "https://www.temu.com/es/search_result.html?search_key={q}" },
    { name: "Miravia", color: "#6B2CF5", url: "https://www.miravia.es/search/?q={q}" },
    { name: "Shein", color: "#222222", url: "https://es.shein.com/pdsearch/{q}/" },
    { name: "eBay", color: "#0064D2", url: "https://www.ebay.es/sch/i.html?_nkw={q}" },
    { name: "Carrefour", color: "#004E9F", url: "https://www.carrefour.es/?q={q}" },
    { name: "El Corte Inglés", color: "#1E7D32", url: "https://www.elcorteingles.es/search-nwx/1/?s={q}" },
    { name: "MediaMarkt", color: "#DF0000", url: "https://www.mediamarkt.es/es/search.html?query={q}" },
    { name: "Idealo", color: "#0A3761", url: "https://www.idealo.es/resultados.html?q={q}", note: "comparador" },
  ],
};
