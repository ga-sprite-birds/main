import { createApp, watch } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import App from "@/App.vue";
import router from "@/router";
import pinia from "@/store";
import i18n from "@/i18n";
import "./assets/styles/common.css";
import { useThemeStore } from "@/store/modules/theme.js";
import { supportedLocales, getDefaultLocale } from "@/i18n/languages.js";

// ── 语言持久化（优先读 localStorage，没有则用 .env 默认）───
const LANG_STORAGE_KEY = "policy_lang";
const savedLang = localStorage.getItem(LANG_STORAGE_KEY);
const allLocales = supportedLocales();
if (savedLang && allLocales.includes(savedLang)) {
    i18n.global.locale.value = savedLang;
} else {
    i18n.global.locale.value = getDefaultLocale();
}

const app = createApp(App);

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
}

app.use(ElementPlus);
app.use(router);
app.use(pinia);
app.use(i18n);

// 主题持久化（已内置在 theme store 中）
const themeStore = useThemeStore();
themeStore.applyTheme();

// 监听语言变化并持久化到 localStorage
watch(
    () => i18n.global.locale.value,
    (newLocale) => {
        localStorage.setItem(LANG_STORAGE_KEY, newLocale);
    },
);

app.mount("#app");
