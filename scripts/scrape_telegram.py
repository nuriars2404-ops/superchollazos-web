#!/usr/bin/env python3
"""Descarga los últimos chollos del canal público de Telegram y genera data/deals.js.

Uso:  python3 scripts/scrape_telegram.py [--pages 15]
Solo usa la librería estándar, así funciona igual en local que en GitHub Actions.
"""
import argparse
import html
import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CHANNEL = "superchollazosysorteos"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "deals.js"
CACHE = ROOT / "data" / "resolved-links.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

CATEGORIES = {
    "Niños y juguetes": r"juguete|niñ[oa]s|bebé|bebe|infantil|lego|playmobil|play-doh|barbie|vtech|peluche|muñec|puzzle|disney|stitch|paw patrol|hot wheels|pañal|beyblade|biberón|biberon|nuk |juego de mesa|juego musical|little live pets|disfraz|first steps",
    "Belleza y cuidado": r"crema|sérum|serum|maquillaje|champú|champu|cabello|pelo|secador|plancha de pelo|rizador|perfume|colonia|uñas|labial|rímel|mascarilla|depiladora|afeitadora|cepillo de dientes|dental|oral-b|facial|skincare|loción|desodorante|gel de ducha|cosmétic|corrector|máscara de pestañas|mascara de pestañas|pestañas|protector solar|spf|urea|íntimo|intimo|desmaquill|granos|capilar|oneblade|pasta de dientes|preservativo|condon|bourjois|essence|rimmel|vichy",
    "Cocina": r"cocina|sartén|sarten|olla|cafetera|café|cafe|freidora|air ?fryer|batidora|tostadora|microondas|vaso|taza|cuchill|tupper|fiambrera|robot de cocina|hervidor|tetera|plato|cubierto|termo|botella|monix|bra |tefal|cecotec|especiero|molde|horno",
    "Hogar y limpieza": r"hogar|limpi|aspirador|fregona|mopa|detergente|suavizante|lavavajillas|toalla|sábana|sabana|edredón|almohada|colchón|cortina|lámpara|lampara|bombilla|organizador|cesto|percha|alfombra|mueble|estantería|deshumidificador|calefactor|radiador|ventilador|manta|cojín|papel higiénico|fairy|ariel|finish|silla|funda nórdica|ropa de cama|ambientador|air wick|antical|calgon|jarra filtradora",
    "Tecnología": r"usb|cable|cargador|auricular|altavoz|bluetooth|móvil|movil|smartphone|iphone|samsung|xiaomi|tablet|portátil|portatil|ordenador|monitor|ratón|raton|teclado|ssd|disco duro|memoria|tarjeta sd|router|wifi|smartwatch|reloj inteligente|power ?bank|batería externa|cámara|camara|alexa|echo|fire tv|kindle|tv |televisor|hdmi|consola|nintendo|playstation|ps5|xbox|arduino|led|joystick|smart tag|batería|bateria",
    "Mascotas": r"perro|gato|mascota|arenero|pienso|comedero|correa|collar para",
    "Coche": r"coche|automóvil|automovil|vehículo|neumático|maletero|volante|parabrisas",
    "Bricolaje y jardín": r"taladro|destornillador|herramienta|bosch|makita|black\+decker|einhell|jardín|jardin|manguera|maceta|planta|tornillo|cinta métrica|nivel láser",
    "Moda": r"camiseta|pantalón|pantalon|vestido|zapatilla|zapato|bota|calcetin|calcetín|sudadera|chaqueta|abrigo|bolso|mochila|cartera|pijama|sujetador|braga|calzoncillo|leggings|gafas de sol|reloj|pulsera|collar|pendiente|levi|adidas|nike|puma|skechers|jeans|chanclas|zip|polo |trunks|botín|botin|sneaker|calzado|pandora|charm|talla",
    "Deporte y salud": r"deporte|fitness|yoga|pesas|mancuerna|bicicleta|running|proteína|proteina|vitamina|suplemento|tensiómetro|termómetro|báscula|bascula|masajeador|colágeno|colageno|magnesio|melatonina|complemento alimenticio",
    "Papelería": r"bolígrafo|boligrafo|lápiz|lapiz|lápices|marcador|cuaderno|stabilo|staedtler|staedler|bic |pocketdoodles",
    "Alimentación": r"chocolate|galleta|café molido|cápsulas|capsulas|aceite de oliva|cerveza|vino |snack|nescafé|nespresso|dolce gusto|cola cao|patatas|refresco|coca-cola|fanta|7 up|nestea|haribo",
}

STORES = {
    "amazon.": "Amazon",
    "aliexpress.": "AliExpress",
    "temu.": "Temu",
    "miravia.": "Miravia",
    "shein.": "Shein",
    "ebay.": "eBay",
    "carrefour.": "Carrefour",
    "elcorteingles.": "El Corte Inglés",
    "pccomponentes.": "PcComponentes",
    "mediamarkt.": "MediaMarkt",
    "fnac.": "Fnac",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def to_float(s):
    s = s.replace("€", "").replace("\xa0", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def clean(fragment):
    fragment = re.sub(r'<i class="emoji"[^>]*><b>(.*?)</b></i>', r"\1", fragment)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ")


def arregla_foto(url):
    """A veces el bot publica fotos de Amazon con la dirección rota (/images/I/ID/AC_...).
    Con el ID se pide la versión buena de 500 px."""
    m = re.match(r"https?://m\.media-amazon\.com/images/I/([A-Za-z0-9+%-]+)/", url)
    return f"https://m.media-amazon.com/images/I/{m.group(1)}._AC_SL500_.jpg" if m else url


def condiciones(text):
    """Lee lo que hace falta para llegar al precio: el código y extras como cupón, CR o descuento al tramitar."""
    code = re.search(r"C[óo]digo:\s*([A-Za-z0-9_-]{3,})", text)
    linea = re.search(r"DESCUENTO:?\s*\d+\s*%([^\n]*)", text)
    conds = []
    for parte in re.split(r"\+", linea.group(1) if linea else ""):
        t = re.sub(r"^con\s+", "", parte.strip(), flags=re.I).strip()
        if not t or re.fullmatch(r"c[óo]digo", t, re.I):
            continue
        t = re.sub(r"\bCR\b", "compra recurrente", t)
        t = re.sub(r"cup[oó]n", "cupón", t, flags=re.I)
        t = re.sub(r"al tr[aá]mit\w*", "al tramitar", t, flags=re.I)
        t = re.sub(r"^(\d+\s*[%€]) cupón$", r"cupón \1", t)
        if t == "al tramitar":
            t = "descuento al tramitar"
        elif re.fullmatch(r"[\d.,]+\s*[%€]", t):
            t += " de descuento"
        conds.append(t)
    if linea and re.search(r"c[óo]digo", linea.group(1), re.I) and not code:
        conds.append("código")
    return (code.group(1) if code else None), conds


def categorize(title):
    t = title.lower()
    for name, pattern in CATEGORIES.items():
        if re.search(pattern, t):
            return name
    return "Otros"


def parse_message(block):
    post = re.search(r'data-post="[^/]+/(\d+)"', block)
    body = re.search(r'js-message_text" dir="auto">(.*?)</div>', block, re.S)
    date = re.search(r'datetime="([^"]+)"', block)
    if not (post and body and date):
        return None
    raw = body.group(1)
    text = clean(raw)

    price = re.search(r"Precio:\s*([\d.,]+)\s*€", text)
    link = re.search(r'ENLACE[^<]*(?:</b>)?\s*<a href="([^"]+)"', raw)
    if not (price and link):
        return None  # sorteos, avisos, mensajes sin formato de chollo

    old = re.search(r"❌\s*([^:\n]+?):+\s*([\d.,]+)\s*€", text)
    disc = re.search(r"DESCUENTO:\s*(\d+)\s*%", text)
    # La foto es el enlace que envuelve el 🔥, o la foto adjunta al mensaje.
    img = re.search(r'<a href="(https?://[^"]+)"[^>]*>\s*<i class="emoji"[^>]*><b>🔥', raw) or \
        re.search(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'", block)

    # El título va entre el enlace de la foto (🔥) y la línea ENLACE.
    title = ""
    m = re.search(r"🔥\s*(.+?)\n\s*\n\s*ENLACE", text, re.S)
    if m:
        title = " ".join(m.group(1).split())
    if not title:
        return None

    p = to_float(price.group(1))
    o = to_float(old.group(2)) if old else None
    d = int(disc.group(1)) if disc else (round((1 - p / o) * 100) if p and o and o > p else None)
    label = old.group(1).strip().capitalize() if old else ""
    label = {"El precio más bajo de los últimos 30 días": "Mínimo 30 días"}.get(label, label)

    return {
        "id": int(post.group(1)),
        "date": date.group(1),
        "title": title,
        "price": p,
        "oldPrice": o,
        "oldLabel": label,
        "discount": d,
        "image": arregla_foto(img.group(1)) if img else None,
        "link": link.group(1),
        "category": categorize(title),
        "code": condiciones(text)[0],
        "conds": condiciones(text)[1],
    }


def resolve(link):
    """Sigue el enlace corto una vez para saber la tienda y el ASIN."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        opener.open(urllib.request.Request(link, method="HEAD", headers={"User-Agent": UA}), timeout=15)
        return link
    except urllib.error.HTTPError as e:
        return e.headers.get("Location") or link
    except Exception:
        return link


def store_info(url):
    host = urlparse(url).netloc.lower()
    store = next((name for key, name in STORES.items() if key in host), "Amazon" if "amzn" in host else "Tienda")
    asin = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    return store, (asin.group(1) if asin else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=15, help="páginas de 20 mensajes a recorrer")
    args = ap.parse_args()

    deals, before = {}, None
    for _ in range(args.pages):
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        page = fetch(url)
        blocks = page.split("tgme_widget_message_wrap")[1:]
        if not blocks:
            break
        ids = []
        for b in blocks:
            d = parse_message(b)
            pid = re.search(r'data-post="[^/]+/(\d+)"', b)
            if pid:
                ids.append(int(pid.group(1)))
            if d:
                deals[d["id"]] = d
        if not ids:
            break
        before = min(ids)

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [d["link"] for d in deals.values() if d["link"] not in cache]
    with ThreadPoolExecutor(8) as pool:
        for link, final in zip(todo, pool.map(resolve, todo)):
            cache[link] = final
    for d in deals.values():
        d["store"], d["asin"] = store_info(cache.get(d["link"], d["link"]))

    out = sorted(deals.values(), key=lambda d: d["id"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    payload = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "channel": CHANNEL, "deals": out}
    OUT.write_text("window.CHOLLOS = " + json.dumps(payload, ensure_ascii=False) + ";\n")
    print(f"{len(out)} chollos guardados en {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
