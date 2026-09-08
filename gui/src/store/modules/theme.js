import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { themeRegistry, normalizeThemeTokens, applyThemeToDocument, resolveThemeRegistryKey } from "@/assets/styles/theme.js";
import i18n from "@/i18n/index.js";

const STORAGE_KEY_FAMILY = "policy_theme_family";
const STORAGE_KEY_MODE = "policy_theme_mode";
const SYSTEM_DARK_MEDIA = "(prefers-color-scheme: dark)";

export const useThemeStore = defineStore("theme", () => {
    const defaultFamily = resolveThemeRegistryKey(import.meta.env.VITE_DEFAULT_THEME_FAMILY, "bootstrap");
    const resolveThemeMode = (mode, fallback = "light") => {
        if (mode === "light" || mode === "dark" || mode === "system") return mode;
        return fallback === "dark" || fallback === "system" ? fallback : "light";
    };

    const systemMedia = typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia(SYSTEM_DARK_MEDIA)
        : null;
    const systemThemeMode = ref(systemMedia?.matches ? "dark" : "light");
    const defaultMode = resolveThemeMode(import.meta.env.VITE_DEFAULT_THEME_MODE, "light");

    const savedFamily = localStorage.getItem(STORAGE_KEY_FAMILY);
    const savedMode = localStorage.getItem(STORAGE_KEY_MODE);

    const themeFamily = ref(resolveThemeRegistryKey(savedFamily, defaultFamily));
    const themeMode = ref(resolveThemeMode(savedMode, defaultMode));
    const effectiveThemeMode = computed(() => (themeMode.value === "system" ? systemThemeMode.value : themeMode.value));

    const currentThemeConfig = computed(() => {
        return themeRegistry[themeFamily.value] || themeRegistry[defaultFamily] || Object.values(themeRegistry)[0];
    });

    const themeType = computed(() => currentThemeConfig.value.type);
    const themeAppearance = computed(() => currentThemeConfig.value.appearance || "standard");
    const themeTokens = computed(() => normalizeThemeTokens(currentThemeConfig.value, effectiveThemeMode.value));
    const isDark = computed(() => effectiveThemeMode.value === "dark");
    const isSystemMode = computed(() => themeMode.value === "system");

    const availableThemes = computed(() => {
        const tFunc = i18n.global.t;
        return Object.values(themeRegistry).map((theme) => ({
            key: theme.key,
            name: tFunc(theme.nameKey || theme.key),
            type: theme.type,
            description: tFunc(theme.descriptionKey || theme.key),
            previewColor: theme.colors.light?.primary || "#409eff",
        }));
    });

    function setThemeFamily(family) {
        const resolvedFamily = resolveThemeRegistryKey(family, defaultFamily);
        if (!resolvedFamily || !themeRegistry[resolvedFamily]) return;
        themeFamily.value = resolvedFamily;
        localStorage.setItem(STORAGE_KEY_FAMILY, resolvedFamily);
        applyTheme();
    }

    function setThemeMode(mode) {
        if (mode !== "light" && mode !== "dark" && mode !== "system") return;
        themeMode.value = mode;
        localStorage.setItem(STORAGE_KEY_MODE, mode);
        applyTheme();
    }

    function toggleThemeMode() {
        setThemeMode(isDark.value ? "light" : "dark");
    }

    function resetTheme() {
        setThemeFamily(defaultFamily);
        setThemeMode(defaultMode);
    }

    function applyTheme() {
        applyThemeToDocument(themeTokens.value, effectiveThemeMode.value, themeFamily.value, themeAppearance.value);
    }

    function init() {
        if (systemMedia) {
            const handleSystemThemeChange = (event) => {
                systemThemeMode.value = event.matches ? "dark" : "light";
                if (themeMode.value === "system") {
                    applyTheme();
                }
            };

            if (!systemMedia.__policyThemeBound) {
                systemMedia.addEventListener("change", handleSystemThemeChange);
                systemMedia.__policyThemeBound = true;
                systemMedia.__policyThemeHandler = handleSystemThemeChange;
            }
        }

        applyTheme();
    }

    return {
        themeFamily,
        themeMode,
        effectiveThemeMode,
        currentThemeConfig,
        themeType,
        themeAppearance,
        themeTokens,
        isDark,
        isSystemMode,
        availableThemes,
        setThemeFamily,
        setThemeMode,
        toggleThemeMode,
        resetTheme,
        applyTheme,
        init,
    };
});
