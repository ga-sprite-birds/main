# Admin Theme Design

> This document defines the GUI theme design, extension rules and boundaries. Read it together
> with [`layout.md`](layout.md): the layout document defines the page skeleton; this document
> defines color semantics for the shell and components.

---

## 1. Goals and scope

The goal is not merely "change a button color", but to establish an extensible, maintainable
theme mechanism that can be adopted incrementally.

The theme system must satisfy:

1. new theme families can be added over time;
2. new themes follow one specification instead of page-local ad-hoc colors;
3. Element Plus theming is reused where possible; the system stays lightweight;
4. the design supports both simple brand-color themes and full visual style themes.

Scope:

1. Admin main-layout pages (`/dashboard`, `/theme`, `/system/config`);
2. Header / Aside / Main / Footer;
3. Element Plus components;
4. project-specific shell styles.

---

## 2. Design principles

### 2.1 Separate layout from theme

- `layout.md` defines the skeleton and regions.
- This document defines color semantics, theme types and extension rules.
- A theme must never change the layout skeleton.

### 2.2 Use semantic tokens, not page-specific styles

Themes define only:

- page background
- surface background
- text color
- border color
- primary accent
- hover / active states

They do not define:

- the title color of a specific business page
- a special button color for one module
- a one-off card style for one page

### 2.3 Dark-mode primary should be slightly brighter

On a dark background, the same primary color used in light mode can look dull and lack contrast.
For every theme, increase the **Lightness** of `primary` in dark mode by roughly 5–10%.

Examples:

- `light.primary: "#409eff"` → `dark.primary: "#3d8bfd"` (slightly brighter)
- `light.primary: "#07c160"` → `dark.primary: "#1aad5b"` (same idea)

This also applies to the `primary` fallback in `systemShell` (the base system shell).

> Rule of thumb: if a button or link looks "sunken" on a dark background, brighten
> `dark.primary`.

### 2.4 Text contrast in dark mode

Dark-mode `pageBg` is usually near-black (e.g. `#0a0a0a`). On that background:

- **Descriptive text and explanatory paragraphs**: do not use `var(--theme-muted-text)` (gray)
  directly; its contrast against near-black often falls below WCAG AA (4.5:1).
- **Recommended**: use `var(--theme-text-color)` with `opacity: 0.65` to keep readability and
  visual hierarchy.

```css
/* Not recommended (contrast may be insufficient in dark mode) */
color: var(--theme-muted-text);

/* Recommended */
color: var(--theme-text-color);
opacity: 0.65;
```

`mutedText` remains suitable for **light mode** or **secondary labels inside tables/cards**
(where the background is `surfaceBg`, not `pageBg`). Do not use it for paragraph-level text
rendered directly on `pageBg`.

### 2.5 Keep it light; prefer Element Plus

- Let Element Plus derive what it can from `primary`.
- Add only the few shell variables that are necessary.
- Do not try to build a huge design system in one step.

### 2.6 Support two theme forms early; normalize consumption later

Themes may be defined in two forms:

1. **Basic theme**: supplies only a primary color.
2. **Style theme**: supplies a full shell palette.

Either way, the system must normalize the result into one set of theme tokens for pages and
components.

---

## 3. Theme model

The theme system uses a **two-axis model**:

1. `themeFamily` — visual family
2. `themeMode` — light / dark

Examples:

- `theme-a + light`
- `theme-a + dark`
- `theme-b + light`
- `theme-b + dark`

Notes:

- `themeFamily` distinguishes visual families.
- `themeMode` distinguishes light/dark.
- Do not reduce the whole system to just `light / dark`.

---

## 4. Theme types

### 4.1 Basic theme

A basic theme is for quick brand-color changes; it does not try to change the whole shell
character.

Characteristics:

1. simple definition;
2. relies mainly on Element Plus primary-color derivation;
3. page background, text hierarchy and borders use the base system shell presets.

Suitable for:

- brand primary color changes
- accent color changes
- extending themes without changing the overall shell character

### 4.2 Style theme

A style theme changes the overall character; it suits IDE/editor/tool-style themes.

Characteristics:

1. more than a primary color;
2. changes background, surface, text, borders, hover and active states together;
3. clearly distinct from the default site style.

Suitable for:

- IDE / editor styles
- tool/workbench styles
- themes with a shell character clearly different from the default site

Current implementation notes:

1. Standard themes use `appearance: "standard"`.
2. The Photoshop CS3 theme uses `appearance: "photoshop-cs3"`.
3. Theme-specific CSS must be scoped by `data-theme-appearance`; never pollute global Element
   Plus styles.
4. When switching back to a standard theme, clear CS3-specific Element variables so hover,
   borders and button texture do not leak into other themes.

Notes:

- Basic and style themes are not mutually exclusive system paths.
- A project can contain several basic themes and several style themes.

---

## 5. Theme definition rules

### 5.1 Required metadata

Every theme provides:

1. `key`: internal identifier, e.g. `theme-a`, `theme-b`
2. `name` / `nameKey`: display name / i18n key
3. `type`: `basic` or `style`
4. `modes`: supported modes, e.g. `light`, `dark`
5. `description` / `descriptionKey`: short description / i18n key
6. `appearance`: `standard` or a dedicated appearance for strong style themes

### 5.2 Required fields for a basic theme

The first version only requires:

1. `primary`

Notes:

- `primary` is the Element Plus primary source.
- `hoverBg` / `activeBg` are derived from the primary color so local modules do not keep the
  system blue.
- Other shell colors come from the system light/dark base presets.
- Do not turn a basic theme into "half a style theme".

### 5.3 Required fields for a style theme

A style theme provides at least:

1. `primary`
2. `pageBg`
3. `surfaceBg`
4. `asideBg`
5. `textColor`
6. `mutedText`
7. `borderColor`
8. `hoverBg`
9. `activeBg`

Notes:

- This is a lightweight but usable minimum shell specification.
- It need not be extremely granular in the first version.
- Additional tokens can be added later, but the specification must be updated centrally; pages
  may not invent fields.

---

## 6. Unified theme-token output

Regardless of whether the source is a basic or style theme, the system outputs the same semantic
tokens.

The unified output includes at least:

1. `primary`
2. `pageBg`
3. `surfaceBg`
4. `asideBg`
5. `textColor`
6. `mutedText`
7. `borderColor`
8. `hoverBg`
9. `activeBg`

Current shell-semantic tokens (already implemented):

1. `workspaceBg`: workspace/canvas background, mainly for tool-style themes such as CS3
2. `controlBg` / `controlBgRaised` / `controlBgSunken`: normal/raised/sunken control backgrounds
3. `headerBg` / `headerText`: top shell background and text
4. `asideText`: sidebar menu text
5. `borderLight` / `borderDark`: highlight/dark edges for skeuomorphic or classic tool themes
6. `surfaceGradientStart` / `surfaceGradientEnd`: panel gradients
7. `insetHighlight` / `insetShadow`: inner highlight and shadow

Normalization rules:

1. **Basic theme**
   - Choose the system base shell preset for the current `themeMode`.
   - Inject the theme's `primary`.
   - Derive `hoverBg` / `activeBg` from `primary` for card tints, active menu items and local
     auxiliary backgrounds.
   - Fill in the complete token set.
2. **Style theme**
   - The theme supplies the full shell fields.
   - The system only fills small fallbacks/compatibility gaps.

Pages and components must consume normalized tokens, not the original theme definition.

---

## 7. Relationship to the layout

Read this with [`layout.md`](layout.md); theme regions map one-to-one to layout regions.

### 7.1 Header

- The Header uses `headerBg`, `headerText` and `borderColor`.
- The theme-mode switcher lives in the Header's right action area.
- Button/icon hover states use `hoverBg` / `activeBg` semantics.

### 7.2 Aside (sidebar)

- The Aside is one of the strongest identity areas of an admin shell.
- Basic themes can keep the base shell.
- Style themes should define `asideBg`, `asideText`, `mutedText`, `hoverBg` and `activeBg`.
- Style identity is usually expressed first in the Aside and Header.

### 7.3 Main content

Per `layout.md`, the main content follows "full-width background, constrained content width", so
theme application has two layers:

1. outer background layer: mainly `pageBg`
2. inner surface/panel/content container: `surfaceBg`, `borderColor`, `textColor`

Notes:

- Do not flatten every Main layer into one color.
- Structure should come from the background and content layers together.
- Separation matters especially on large screens.

### 7.4 Footer

- The Footer appears only in the admin main layout.
- Share shell semantics with the Header to avoid a split look.
- Prefer `surfaceBg`, `borderColor` and `mutedText`.

---

## 8. `.env`, browser storage and backend responsibilities

### 8.1 `.env` responsibilities

The GUI uses Vite modes:

1. `.env`: shared GUI identity
2. `.env.development`: local development
3. `.env.production`: production build

`.env` should contain only cross-environment display identity:

```env
VITE_APP_TITLE=GA Sprite Birds
VITE_COMPANY_NAME=GA Sprite Birds
VITE_APP_BUILD_VERSION=b-2026.11.12
```

`.env.development` / `.env.production` hold environment-specific API and theme defaults:

```env
VITE_API_BASE_URL=
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
VITE_API_PREFIX=/fcgi-bin/api
VITE_DEFAULT_THEME_FAMILY=photoshop
VITE_DEFAULT_THEME_MODE=system
VITE_DEFAULT_LANG=zh_CN
```

Production example:

```env
VITE_API_BASE_URL=
VITE_API_PREFIX=/fcgi-bin/api
VITE_DEFAULT_THEME_FAMILY=photoshop
VITE_DEFAULT_THEME_MODE=system
VITE_DEFAULT_LANG=zh_CN
```

`VITE_DEFAULT_THEME_FAMILY` options: `bootstrap`, `wechat`, `orange`, `cherryRed`, `photoshop`.

Do not put in env:

1. per-theme concrete color values;
2. a large number of ad-hoc tokens;
3. page-level theme details.

Compatibility notes:

- the legacy family name `notepadpp` maps to `bootstrap`;
- an unknown theme family falls back to the current environment default;
- if the default is unavailable, it falls back to the first registered theme.

### 8.2 Browser storage

Persist the user's actual choice in the browser:

1. `themeFamily`
2. `themeMode`

Advantages:

1. simple;
2. no backend round-trip;
3. preferences survive refresh/re-login on the same machine.

### 8.3 Backend responsibility (optional, later)

If cross-device per-account theme preferences are required later, add backend storage.

At this stage:

- the backend is not a prerequisite for theming;
- frontend-local persistence is sufficient.

### 8.4 Theme compliance rules

Business pages and layout components must:

1. use `--theme-*` semantic tokens for background, text, borders, hover and active states;
2. use Element Plus `primary` for primary buttons, links, switches and pagination;
3. never hard-code concrete theme colors such as `#409eff` or `#304156` in ordinary pages;
4. read preview colors on the theme settings page from `normalizeThemeTokens`, not from a fixed
   default theme;
5. allow color values only in `theme.js`, `variables.css`, and strong-style theme CSS scoped by
   `data-theme-appearance`.

The audio workbench and theme settings page have been checked against these rules: uploads,
forms, tables, progress, drawers and menus consume theme tokens or Element Plus variables.

---

## 9. Adding a theme

1. Choose the family key and display name.
2. Choose the type: basic or style.
3. Choose `appearance`: `standard` for standard themes, a dedicated appearance for strong styles.
4. Fill in the required fields for that type.
5. Connect it to unified token normalization.
6. If Element Plus styles must be overridden, scope them with `data-theme-appearance`.
7. Verify these UI areas:
   - list pages
   - form pages
   - dialogs
   - tables
   - Header / Aside / Footer
8. Switch back to other themes and confirm no hover, border, button, pagination or table styles
   leak.
9. Document the theme's purpose and design intent.

---

## 10. Prohibited

1. No `if theme === 'xxx'` branches in business pages.
2. No half-filled token sets that leave old colors on some pages.
3. No hard-coded theme colors that bypass semantic tokens.
4. No elevating a one-page visual rule into a global theme rule.
5. To add a theme field, update this specification first, then change the implementation.

---

## 11. Summary

The admin theme system uses:

1. a `themeFamily + themeMode` two-axis model;
2. two theme forms: basic and style;
3. basic themes supply a primary color; style themes supply a minimum shell palette;
4. internal normalization to semantic tokens consumed by pages/components;
5. `.env` provides defaults only; the user's actual choice lives in the browser;
6. each project chooses its default family through env defaults.

This keeps theme development constrained as the product grows.

---

## 12. Secondary development and theme customization

> This section is for reusing the project as an admin theme framework: replace brand colors and
> extend themes without breaking theme isolation or Element Plus principles.

### 12.1 Recommended order

1. Confirm the app name, default language and default theme.
2. Decide between "brand color only" and "full style theme".
3. Adjust a small number of business-page styles last.

Relevant files:

```text
.env                              cross-environment display identity
.env.development                  local API + default theme
.env.production                   production API + default theme
src/assets/styles/theme.js        theme registry, token normalization, Element Plus variables
src/assets/styles/variables.css   CSS variable definitions
src/assets/styles/common.css      global styles + scoped strong-theme overrides
src/store/modules/theme.js        theme state, browser persistence, fallbacks
src/components/layout/*.vue       Header / Sidebar / Main / Footer shell
src/views/audio/*.vue             audio workbench (consumes theme tokens)
```

### 12.2 Brand primary color only

Prefer adding/modifying a `basic` theme.

1. Add a theme key in `themeRegistry`.
2. Set `type: "basic"`.
3. Set `appearance: "standard"`.
4. Configure `colors.light.primary` and `colors.dark.primary`.
5. Do not override Header, Sidebar, table or button component styles.

Example:

```js
brand: {
  key: "brand",
  appearance: "standard",
  name: "Brand",
  nameKey: "theme.name.brand",
  type: "basic",
  modes: ["light", "dark"],
  description: "Brand palette",
  descriptionKey: "theme.desc.brand",
  colors: {
    light: { primary: "#1677ff" },
    dark: { primary: "#4096ff" },
  },
}
```

Suitable for:

1. most admin systems;
2. brand-color differentiation only;
3. minimal custom CSS.

### 12.3 Full visual style

Add a `style` theme when the shell character must change (like Photoshop CS3).

1. Provide both light and dark token sets in `themeRegistry`.
2. Give the theme a dedicated `appearance`, e.g. `appearance: "my-theme"`.
3. Scope all special CSS as `:root[data-theme-appearance="my-theme"] ...`.
4. Switching back to `standard` must leave no hover, border, shadow or button residue.
5. If you add a token, update this document before changing code.

Avoid:

1. `themeFamily === "xxx"` checks in business pages;
2. adding a global theme variable for one page;
3. overriding `.el-button`, `.el-table` etc. without theme scoping;
4. detaching Element Plus components from its variable system.

### 12.4 Modifying an existing theme

Change tokens first, not CSS everywhere.

Priority:

1. If `primary` solves it, change only `primary`.
2. If `pageBg`, `surfaceBg`, `textColor` or `borderColor` solves it, change only tokens.
3. Add scoped CSS in `common.css` only for strong-style texture.
4. If component internals seem to need changes, decide whether it is actually a layout issue.

Quick diagnosis:

1. wrong colors → `theme.js`
2. hover/border/shadow residue → `common.css` scoping
3. wrong Header/Sidebar/Main region colors → layout components consuming tokens
4. uncomfortable page width → `layout.md` and `page-container--*`, not the theme system

### 12.5 Element Plus principles

1. Write the primary color to `--el-color-primary`.
2. Sync background/text/border to Element Plus variables where practical.
3. Keep dark mode via the root `.dark` class and Element Plus dark variables.
4. Standard themes do not redraw components at scale.
5. Strong-style themes may override component texture under their own `data-theme-appearance`.

Benefits:

1. safer Element Plus upgrades;
2. new business pages need little component-specific adaptation;
3. no half-old/half-new residue when switching themes;
4. new projects only need to understand tokens, not all component CSS.

### 12.6 `.env` recommendations

When reusing the project, change:

```env
VITE_APP_TITLE=Your Admin
VITE_APP_BUILD_VERSION=1.0.0
VITE_COMPANY_NAME=Your Company
```

Notes:

1. `.env` holds shared display identity only.
2. `VITE_DEFAULT_THEME_FAMILY` lives in `.env.development` / `.env.production` and sets the
   default theme only.
3. The user's chosen theme is persisted in the browser.
4. An unknown theme key falls back to the default.
5. This project has no login mode or token configuration.

### 12.7 Acceptance checklist

1. Audio generation workbench.
2. Theme settings page.
3. Tables, uploads, forms and progress states.
4. Dialogs, drawers and dropdown menus.
5. Switches, inputs and selectors.
6. Header, Sidebar and Footer.
7. Light and dark modes.
8. Switch from the new theme back to others and confirm no hover, border, background or button
   residue.

For a brand-color-only theme, checking 1–5 is usually enough. For a strong style theme, check all
1–8.

### 12.8 Recommended boundaries

1. The theme system owns visual semantics, not business layout.
2. The layout system owns skeletons and content width, not brand colors.
3. Business pages consume tokens and page-container classes; they never branch on theme names.
4. Login pages, if added, may have their own visuals but must still consume global theme tokens.
5. Add new themes through the registry and tokens first; CSS overrides come last.

One-line rule:

> Change tokens before scoped CSS; follow Element Plus before adding texture; guarantee theme
> isolation before pursuing visual personality.
