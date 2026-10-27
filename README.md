# Superchollazos · web de chollos diarios

Web estática que muestra los chollos del canal de Telegram @superchollazosysorteos, con buscador y comparador de precios en otras tiendas.

## Ver la web en tu ordenador

```bash
cd ~/superchollazos-web
python3 -m http.server 8765
```

Abre http://localhost:8765

## Actualizar los chollos a mano

```bash
python3 scripts/scrape_telegram.py
```

Lee la vista pública del canal (t.me/s/superchollazosysorteos), saca precio, descuento, foto, título y enlace de cada mensaje y lo guarda en `data/deals.js`. Los mensajes que no son chollos (sorteos, avisos) se ignoran.

## Publicarla gratis y que se actualice sola

1. Crea un repositorio en GitHub y sube esta carpeta.
2. En el repositorio: Settings → Pages → Source: "Deploy from a branch" → rama `main`, carpeta `/ (root)`.
3. La acción `.github/workflows/actualizar-chollos.yml` vuelve a leer el canal cada 30 minutos y publica los chollos nuevos sola.

También vale Netlify, Vercel o Cloudflare Pages: es una web estática sin compilar.

## Ajustes

- `assets/config.js`: etiqueta de afiliada de Amazon y tiendas del comparador.
- `scripts/scrape_telegram.py`: palabras clave de cada categoría (`CATEGORIES`).
