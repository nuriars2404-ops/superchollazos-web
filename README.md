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

1. Crea un repositorio público vacío en https://github.com/new llamado `superchollazos-web`.
2. Súbelo:
   ```bash
   git remote add origin https://github.com/nuriars2404-ops/superchollazos-web.git
   git push -u origin main
   ```
3. En el repositorio: Settings → Pages → Source: **GitHub Actions**.
4. Settings → Actions → General → Workflow permissions: **Read and write permissions**.

A partir de ahí, la acción `.github/workflows/actualizar-chollos.yml` lee el canal cada 10 minutos y publica la web en https://nuriars2404-ops.github.io/superchollazos-web/. Quien tenga la web abierta ve los chollos nuevos sin recargar (se comprueba cada 2 minutos).

## Ajustes

- `assets/config.js`: etiqueta de afiliada de Amazon y tiendas del comparador.
- `scripts/scrape_telegram.py`: palabras clave de cada categoría (`CATEGORIES`).
