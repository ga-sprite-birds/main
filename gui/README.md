# GA Sprite Birds GUI

A Vue 3 + Element Plus + Pinia + Vite frontend for the FastAPI backend. The theme shell is
derived from `tiger-backend-themes`; login and authentication pages have been removed.

## Development

```bash
npm install
npm run dev
```

The Vite dev server proxies `/fcgi-bin` to the API (default `http://localhost:8000`; override with
`VITE_API_PROXY_TARGET`).

Production build:

```bash
npm run build
```

This writes the single-file `../index.html` at the repository root.

## Environment configuration

The project uses Vite env modes:

- `.env`: shared display identity (title, company name, build version).
- `.env.development`: local development, including the API proxy and default theme.
- `.env.production`: production build, including the production API and default theme.

Common theme settings:

```env
VITE_DEFAULT_THEME_FAMILY=photoshop
VITE_DEFAULT_THEME_MODE=system
```

Available themes:

- `bootstrap`
- `wechat`
- `orange`
- `cherryRed`
- `photoshop`

## Using themes

Do not hard-code theme colors in pages; use the semantic variables:

```css
background: var(--theme-surface-bg);
color: var(--theme-text-color);
border-color: var(--theme-border-color);
```

Prefer `type="primary"` for Element Plus buttons, switches, pagination and similar components; the
theme system writes the current primary color into Element Plus CSS variables.

To add a brand-color theme, usually you only need to register a new `type: "basic"` theme in
`src/assets/styles/theme.js` and set `primary`. The system derives the hover/active auxiliary
colors automatically.

Full guides: [`help/theme.md`](help/theme.md) and [`help/layout.md`](help/layout.md).
