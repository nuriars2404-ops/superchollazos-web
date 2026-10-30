#!/usr/bin/env python3
"""Consulta el precio actual de los chollos en Amazon y AliExpress y genera data/precios.js.

Las claves llegan por variables de entorno (secretos de GitHub) y nunca se escriben en el registro.
Si una tienda falla o le faltan claves, se avisa y se sigue: la web publica los chollos igualmente.
"""
import hashlib
import hmac
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "data" / "deals.js"
OUT = ROOT / "data" / "precios.js"
HISTORIAL = ROOT / "data" / "historial.json"

AMAZON_CADUCA = 3600  # Amazon pide datos recientes: se renuevan cada hora
ALI_CADUCA = 24 * 3600
ALI_POR_PASADA = 25  # productos nuevos por ejecución, para no agotar el cupo de la API
COINCIDENCIA_MIN = 0.6  # parte de las palabras del producto que debe tener el resultado de AliExpress
DIAS_GUARDADOS = 180
DIAS_MINIMOS = 14  # con menos historial no se afirma que un precio sea el más bajo
PALABRAS_VACIAS = {"para", "con", "de", "del", "los", "las", "una", "uno", "pack"}


def ahora():
    return int(time.time())


def carga_js(path):
    if not path.exists():
        return {}
    t = path.read_text()
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def palabras(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2 and w not in PALABRAS_VACIAS}


def nombre_corto(title):
    head = re.split(r"\s[|–]\s|,|\|", title)[0].strip()
    return " ".join(head.split()[:8])


def precios_amazon(deals, guardados):
    cid, secret = os.environ.get("AMAZON_CREDENTIAL_ID"), os.environ.get("AMAZON_CREDENTIAL_SECRET")
    version = os.environ.get("AMAZON_CREDENTIAL_VERSION")
    if not (cid and secret and version):
        print("Amazon: faltan claves, se omite")
        return
    from amazon_creatorsapi import AmazonCreatorsApi
    from creatorsapi_python_sdk.models.get_items_resource import GetItemsResource as R

    tag = os.environ.get("AMAZON_TAG", "doradita-21")  # la etiqueta asociada a estas claves
    tag_enlaces = os.environ.get("AMAZON_TAG_ENLACES", "laurasoyyo02-21")  # la que llevan los enlaces de la web
    asins = sorted({d["asin"] for d in deals if d.get("asin")
                    and ahora() - guardados.get(d["asin"], {}).get("amazon", {}).get("t", 0) > AMAZON_CADUCA})
    if not asins:
        print("Amazon: nada que actualizar")
        return
    api = AmazonCreatorsApi(credential_id=cid, credential_secret=secret, version=version, tag=tag, country="ES")
    items = api.get_items(asins, resources=[R.OFFERS_V2_DOT_LISTINGS_DOT_PRICE])
    ok = 0
    for it in items:
        listings = it.offers_v2.listings if it.offers_v2 and it.offers_v2.listings else []
        if listings and listings[0].price and listings[0].price.money:
            guardados.setdefault(it.asin, {})["amazon"] = {
                "precio": float(listings[0].price.money.amount),
                "url": re.sub(r"([?&]tag=)[^&]+", r"\g<1>" + tag_enlaces, it.detail_page_url), "t": ahora()}
            ok += 1
    print(f"Amazon: {ok} precios de {len(asins)} productos")


def llama_aliexpress(metodo, params, key, secret):
    """Pasarela de AliExpress: firma HMAC-SHA256 de los parámetros ordenados."""
    p = {"app_key": key, "method": metodo, "sign_method": "sha256", "timestamp": str(ahora() * 1000),
         "format": "json", "v": "2.0", **params}
    base = "".join(k + str(p[k]) for k in sorted(p))
    p["sign"] = hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()
    url = "https://api-sg.aliexpress.com/sync?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def precios_aliexpress(deals, guardados):
    key, secret = os.environ.get("ALIEXPRESS_APP_KEY"), os.environ.get("ALIEXPRESS_APP_SECRET")
    tracking = os.environ.get("ALIEXPRESS_TRACKING_ID")
    if not (key and secret and tracking):
        print("AliExpress: faltan claves, se omite")
        return
    pendientes = [d for d in deals
                  if ahora() - guardados.get(d.get("asin") or str(d["id"]), {}).get("ali_t", 0) > ALI_CADUCA]
    ok = 0
    for d in pendientes[:ALI_POR_PASADA]:
        clave = d.get("asin") or str(d["id"])
        q = nombre_corto(d["title"])
        data = llama_aliexpress("aliexpress.affiliate.product.query", {
            "keywords": q, "tracking_id": tracking, "target_currency": "EUR", "target_language": "ES",
            "ship_to_country": "ES", "sort": "SALE_PRICE_ASC", "page_size": "20"}, key, secret)
        if "error_response" in data:
            e = data["error_response"]
            print("AliExpress: error de la API:", e.get("code"), e.get("msg"), e.get("sub_msg", ""))
            return
        res = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result") or {}
        productos = (res.get("products") or {}).get("product") or []
        buscadas = palabras(q)
        parecidos = [p for p in productos
                     if buscadas and len(buscadas & palabras(p.get("product_title", ""))) / len(buscadas) >= COINCIDENCIA_MIN]
        g = guardados.setdefault(clave, {})
        g["ali_t"] = ahora()
        parecidos = [p for p in parecidos if p.get("promotion_link")]  # sin enlace de afiliada no hay comisión
        if parecidos:
            mejor = min(parecidos, key=lambda p: float(p.get("target_sale_price") or 1e9))
            g["ali"] = {"precio": float(mejor["target_sale_price"]), "url": mejor["promotion_link"],
                        "titulo": mejor.get("product_title", ""), "t": ahora()}
            ok += 1
        else:
            g.pop("ali", None)
        time.sleep(1)
    print(f"AliExpress: {ok} coincidencias en {min(len(pendientes), ALI_POR_PASADA)} productos revisados")


def actualiza_historial(deals, guardados, hoy=None):
    """Guarda el precio más bajo de cada día (tienda o canal) y marca los chollos que son mínimo real.

    En los chollos con código se compara el precio con código, que es el que paga la gente.
    Sin código, además, la tienda debe seguir a ese precio: si ha subido, la oferta ya no vale.
    """
    hoy = hoy or datetime.now(timezone.utc).date()
    hist = json.loads(HISTORIAL.read_text()) if HISTORIAL.exists() else {}
    anota = lambda asin, dia, precio: hist.setdefault(asin, {}).__setitem__(
        dia, min(precio, hist.get(asin, {}).get(dia, precio)))
    for d in deals:
        if d.get("asin") and d.get("price"):
            anota(d["asin"], d["date"][:10], d["price"])
    for asin, g in guardados.items():
        if g.get("amazon"):
            anota(asin, hoy.isoformat(), g["amazon"]["precio"])
    limite = (hoy - timedelta(days=DIAS_GUARDADOS)).isoformat()
    hist = {a: {k: v for k, v in dias.items() if k >= limite} for a, dias in hist.items()}
    hist = {a: dias for a, dias in hist.items() if dias}
    HISTORIAL.write_text(json.dumps(hist, separators=(",", ":"), sort_keys=True))

    ultimo = {}
    for d in sorted(deals, key=lambda x: x["date"]):
        if d.get("asin"):
            ultimo[d["asin"]] = d
    marcados = 0
    for asin, d in ultimo.items():
        g = guardados.setdefault(asin, {})
        g.pop("minimo", None)
        dia = d["date"][:10]
        anteriores = {k: v for k, v in hist.get(asin, {}).items() if k < dia}
        if not anteriores:
            continue
        dias = (date.fromisoformat(dia) - date.fromisoformat(min(anteriores))).days
        tienda = g.get("amazon", {}).get("precio")
        vale = bool(d.get("code") or d.get("conds")) or (tienda is not None and tienda <= d["price"])
        if dias >= DIAS_MINIMOS and vale and d["price"] < min(anteriores.values()):
            g["minimo"] = {"dias": dias}
            marcados += 1
    print(f"Historial: {len(hist)} productos, {marcados} en su precio más bajo")


def main():
    deals = carga_js(DEALS).get("deals", [])
    guardados = carga_js(OUT)
    for nombre, fn in (("Amazon", precios_amazon), ("AliExpress", precios_aliexpress)):
        try:
            fn(deals, guardados)
        except Exception as e:  # una tienda caída no debe parar la publicación de los chollos
            print(f"{nombre}: fallo {type(e).__name__}: {e}")
    try:
        actualiza_historial(deals, guardados)
    except Exception as e:
        print(f"Historial: fallo {type(e).__name__}: {e}")
    vigentes = {d.get("asin") or str(d["id"]) for d in deals}
    guardados = {k: v for k, v in guardados.items() if k in vigentes}
    OUT.write_text("window.PRECIOS = " + json.dumps(guardados, ensure_ascii=False) + ";\n")
    print(f"{len(guardados)} productos con datos; {datetime.now(timezone.utc):%H:%M} UTC")


if __name__ == "__main__":
    main()
