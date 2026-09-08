# GA Sprite Birds GUI

基于 Vue3、Element Plus、Pinia、Vite 的 FastAPI 图形界面。主题骨架沿用 `tiger-backend-themes`，登录和鉴权页面已移除。

## 启动

```bash
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

## 环境配置

项目使用 Vite env mode：

- `.env`：公共展示身份，如标题、公司名、构建版本。
- `.env.development`：本地开发配置，包含 API 代理和默认主题。
- `.env.production`：生产构建配置，包含线上 API 和默认主题。

常用主题配置：

```env
VITE_DEFAULT_THEME_FAMILY=bootstrap
VITE_DEFAULT_THEME_MODE=system
```

可用主题：

- `bootstrap`
- `wechat`
- `orange`
- `cherryRed`
- `photoshop`

## 主题使用

页面不要直接写死主题色，优先使用语义变量：

```css
background: var(--theme-surface-bg);
color: var(--theme-text-color);
border-color: var(--theme-border-color);
```

主按钮、开关、分页等 Element Plus 组件优先使用 `type="primary"`，主题系统会把当前主色写入 Element Plus CSS 变量。

新增品牌色主题时，通常只需要在 `src/assets/styles/theme.js` 里新增一个 `type: "basic"` 主题并配置 `primary`。系统会自动推导基础主题的 hover / active 辅助色。

完整说明见 `help/主题.md`。
