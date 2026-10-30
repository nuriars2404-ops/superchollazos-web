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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "data" / "deals.js"
OUT = ROOT / "data" / "precios.js"

AMAZON_CADUCA = 3600  # Amazon pide datos recientes: se renuevan cada hora
ALI_CADUCA = 24 * 3600
ALI_POR_PASADA = 25  # productos nuevos por ejecución, para no agotar el cupo de la API
COINCIDENCIA_MIN = 0.6  # parte de las palabras del producto que debe tener el resultado de AliExpress
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

    tag = os.environ.get("AMAZON_TAG", "doradita-21")
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
                "precio": float(listings[0].price.money.amount), "url": it.detail_page_url, "t": ahora()}
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
        if parecidos:
            mejor = min(parecidos, key=lambda p: float(p.get("target_sale_price") or 1e9))
            g["ali"] = {"precio": float(mejor["target_sale_price"]), "url": mejor.get("promotion_link") or mejor.get("product_detail_url"),
                        "titulo": mejor.get("product_title", ""), "t": ahora()}
            ok += 1
        else:
            g.pop("ali", None)
        time.sleep(1)
    print(f"AliExpress: {ok} coincidencias en {min(len(pendientes), ALI_POR_PASADA)} productos revisados")


def main():
    deals = carga_js(DEALS).get("deals", [])
    guardados = carga_js(OUT)
    for nombre, fn in (("Amazon", precios_amazon), ("AliExpress", precios_aliexpress)):
        try:
            fn(deals, guardados)
        except Exception as e:  # una tienda caída no debe parar la publicación de los chollos
            print(f"{nombre}: fallo {type(e).__name__}: {e}")
    vigentes = {d.get("asin") or str(d["id"]) for d in deals}
    guardados = {k: v for k, v in guardados.items() if k in vigentes}
    OUT.write_text("window.PRECIOS = " + json.dumps(guardados, ensure_ascii=False) + ";\n")
    print(f"{len(guardados)} productos con datos; {datetime.now(timezone.utc):%H:%M} UTC")


if __name__ == "__main__":
    main()
