# Admin Layout Design

> This document defines the base layout structure for the GA Sprite Birds GUI. The project has no
> login page.

---

## 1. Routing and scope

### 1.1 Router mode

The project uses **History mode** (`createWebHistory`); URLs look like `/dashboard` and contain no `#`.

> **Deployment note:** History mode requires the server to fall back all route requests to
> `index.html`, otherwise a refresh returns 404.
>
> Nginx example:
> ```nginx
> location / {
>     try_files $uri $uri/ /index.html;
> }
> ```
>
> The Vite dev server includes this fallback, so no extra configuration is needed locally.

### 1.2 Route-to-layout mapping

1. Business routes (`/dashboard`, `/theme`, `/system/config`)
   - All use the **admin main layout**.
   - The layout renders: top header + left sidebar + right content + bottom footer.

---

## 2. Overall structure

The page is split into three blocks:

1. Top **Header** (full width; logo + action area)
2. Middle: **left sidebar + right content** (with a reserved secondary-navigation area)
3. Bottom **Footer** (admin layout only)

The shell spans the full width; the main content follows the principle
"**full-width background, constrained content width**", similar to mature admin templates.

---

## 3. Header

### 3.1 Position and width

- Position: top of the page, full width (100%).
- Internal layout: flex; left side fixed at 200px, right side fluid.

### 3.2 Left logo area (fixed 200px)

- Fixed width: 200px.
- Content is horizontally and vertically centered.
- Displays:
  - `VITE_APP_TITLE` as the system name (e.g. `GA Sprite Birds`);
  - icons/logo can be added here later alongside the text.

### 3.3 Right action area (fluid, right-aligned)

- Occupies the remaining width.
- Flex layout, aligned to the right.
- Contains:
  1. theme-mode dropdown (light / dark / system);
  2. language switcher;
  3. service status (Control API + Core engine).

### 3.4 Header button color inheritance

All Header buttons (theme, language, etc.) must inject their text color explicitly with
`:style="{ color: headerTextColor }"` instead of relying on CSS `color: inherit`.

Reason: `el-dropdown` trigger slots create extra DOM wrappers, which break the `color: inherit`
chain; standard `el-button` is affected too.

```vue
<el-button :style="{ color: headerTextColor }" text>
  Language
</el-button>
```

`headerTextColor` comes from `var(--theme-header-text)`, provided by the theme system.

---

## 4. Middle area: sidebar + content

### 4.1 Left sidebar (fixed 200px)

- Fixed width: 200px.
- Implemented with Element Plus `el-aside` + `el-menu`.
- Current menu:
  - **Dashboard** (`/dashboard`)
  - **System config** (`/system/config`) with the seven config sections
  - **Theme** (`/theme`)
- Do not add entries for features the backend does not support.

### 4.2 Right content area (fluid)

The content area has two layers:

1. Optional secondary navigation / tab bar (reserved)
   - Position: directly below the Header, above the main content.
   - Future use: sub-navigation, tabs, breadcrumbs.
   - Currently controlled by route meta; can be hidden when empty.
2. Main content area
   - Hosts the current route (`<router-view />`).
   - Fluid width; height grows with content.
   - The outer shell stays full width; the inner content is constrained by page type.
   - Visual control follows "**full-width shell background; content width chosen per page**".

### 4.3 Main content width conventions

All admin pages rendered inside `main` follow these rules:

1. **Outer shell is full width**
   - `el-main` fills the available space.
   - Page background, spacing and scrolling are handled by the main layout.

2. **List / search / table pages default to full width**
   - Pages focused on information density (lists, searches, tables, dashboards) use full width.
   - Avoid wasting horizontal space on laptop screens.
   - Very wide tables should scroll horizontally or control column widths; do not squeeze the
     whole page into a narrow card.

3. **Form / detail / focused-operation pages constrain content width**
   - White cards, module backgrounds and stepper containers stay full width by default.
   - The actual title, form, steps and detail body sit inside an inner content container.
   - The inner container's max width should feel comfortable on a full-screen laptop.
   - Neither extremely narrow/centered nor stretched across 2K/4K screens.

4. **Page width classes**
   - `page-container`: base page container, full available width.
   - `page-container--fluid`: list/search/table pages; no max width.
   - `page-container--comfortable`: regular forms, details, theme settings; max width ~1200px.
   - `page-container--narrow`: simple forms and small local config pages; max width ~960px.
   - `page-container--wide`: complex config and large dashboards; max width ~1440px.

5. **Design principle**
   - The background carries page structure and hierarchy.
   - The content layer controls reading width and interaction density.
   - This avoids a loose look on large screens while keeping laptops well utilized.

6. **Applicability**
   - Form pages: create, edit, detail, parameter configuration.
   - Composite configuration pages: split-pane settings, multi-step setup, mixed content.
   - List pages prefer `page-container--fluid` so the query bar, toolbar and table get full width.
   - Very wide tables may use a wider inner content layer, but avoid uncontrolled stretching.

7. **Confirmed implementation policy**
   - `main` uses one strategy: **full-width shell background; content width chosen per page**.
   - This can be reused by other admin modules/projects.
   - Unless a page has special business requirements, do not design "shrink the entire white card".

---

## 5. Footer

### 5.1 Visibility

- Shown only in the admin main layout.

### 5.2 Content and format

- Right-aligned, two lines:

1. First line:
   - `{appTitle} {management-system label} build-{VITE_APP_BUILD_VERSION}`
   - `{appTitle}` comes from `VITE_APP_TITLE`;
   - the build version comes from `VITE_APP_BUILD_VERSION`.
2. Second line:
   - `©{year} {VITE_COMPANY_NAME} Corporation. All Rights Reserved.`
   - `VITE_COMPANY_NAME` falls back to `VITE_APP_TITLE`.

---

## 6. Implementation notes

1. Use the Element Plus `el-container` family:
   - `el-header` / `el-aside` / `el-main` / `el-footer`;
   - combine with flex for horizontal layout and alignment.
2. Use two layers in `main`:
   - Layer 1: full-width page/card/background block;
   - Layer 2: max-width content container for steps, forms, filters and body text.
3. Theme and i18n:
   - the Header already supports theme switching (Pinia + CSS variables);
   - all copy should be in the i18n language packs.
