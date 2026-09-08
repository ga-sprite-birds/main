/*
 * Theme token registry and DOM application helpers.
 * The Photoshop family intentionally exposes a richer shell so CSS can
 * recreate the CS3-style raised/sunken panel structure.
 */

export const systemShell = {
    light: {
        primary: "#409eff",
        pageBg: "#f0f2f5",
        surfaceBg: "#ffffff",
        asideBg: "#f5f5f5",
        workspaceBg: "#eef1f4",
        controlBg: "#f7f7f7",
        controlBgRaised: "#ffffff",
        controlBgSunken: "#eef1f2",
        headerBg: "#ffffff",
        headerText: "#303133",
        asideText: "#303133",
        textColor: "#303133",
        mutedText: "#909399",
        borderColor: "#e4e7ed",
        borderLight: "#ffffff",
        borderDark: "#c8ccd4",
        hoverBg: "#ecf5ff",
        activeBg: "#d9ecff",
        surfaceGradientStart: "#ffffff",
        surfaceGradientEnd: "#f6f8fb",
        insetHighlight: "rgba(255,255,255,0.8)",
        insetShadow: "rgba(0,0,0,0.08)",
    },
    dark: {
        primary: "#3d8bfd",
        pageBg: "#0a0a0a",
        surfaceBg: "#1a1a1a",
        asideBg: "#141414",
        workspaceBg: "#0f1011",
        controlBg: "#202224",
        controlBgRaised: "#2a2d30",
        controlBgSunken: "#151719",
        headerBg: "#1a1a1a",
        headerText: "#e0e0e0",
        asideText: "rgba(255,255,255,0.78)",
        textColor: "#e0e0e0",
        mutedText: "#666666",
        borderColor: "#333333",
        borderLight: "#4a4f57",
        borderDark: "#111214",
        hoverBg: "#2a2a2a",
        activeBg: "#3a3a3a",
        surfaceGradientStart: "#2b2e33",
        surfaceGradientEnd: "#1f2226",
        insetHighlight: "rgba(255,255,255,0.05)",
        insetShadow: "rgba(0,0,0,0.45)",
    },
};

const themeAliases = {
    notepadpp: "bootstrap",
};

function normalizeHexColor(color) {
    if (typeof color !== "string") return null;

    const value = color.trim().replace(/^#/, "");
    if (value.length === 3) {
        return `#${value
            .split("")
            .map((char) => `${char}${char}`)
            .join("")}`.toLowerCase();
    }
    if (value.length === 6) {
        return `#${value}`.toLowerCase();
    }

    return null;
}

function hexToRgb(color) {
    const normalized = normalizeHexColor(color);
    if (!normalized) return null;

    return {
        r: parseInt(normalized.slice(1, 3), 16),
        g: parseInt(normalized.slice(3, 5), 16),
        b: parseInt(normalized.slice(5, 7), 16),
    };
}

function mixHexColors(color, target, weight) {
    const sourceRgb = hexToRgb(color);
    const targetRgb = hexToRgb(target);

    if (!sourceRgb || !targetRgb) return color;

    const mixChannel = (sourceChannel, targetChannel) => {
        return Math.round(sourceChannel + (targetChannel - sourceChannel) * weight)
            .toString(16)
            .padStart(2, "0");
    };

    return `#${mixChannel(sourceRgb.r, targetRgb.r)}${mixChannel(sourceRgb.g, targetRgb.g)}${mixChannel(sourceRgb.b, targetRgb.b)}`;
}

function buildPrimaryScale(tokens) {
    const primary = normalizeHexColor(tokens.primary) || "#409eff";
    const primaryRgb = hexToRgb(primary) || { r: 64, g: 158, b: 255 };
    const primaryLightColors = {};

    for (let level = 1; level <= 9; level += 1) {
        primaryLightColors[level] = mixHexColors(primary, "#ffffff", level / 10);
    }

    if (tokens.primaryLight3) {
        primaryLightColors[3] = tokens.primaryLight3;
    }

    return {
        primary,
        primaryRgb: `${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}`,
        primaryLightColors,
        primaryDark2: tokens.primaryDark2 || mixHexColors(primary, "#000000", 0.2),
    };
}

function buildBasicThemeShellTokens(shell, themeColors, mode) {
    const primary = normalizeHexColor(themeColors.primary) || shell.primary;
    const isDark = mode === "dark";

    return {
        primary,
        hoverBg: isDark
            ? mixHexColors(primary, shell.surfaceBg, 0.85)
            : mixHexColors(primary, "#ffffff", 0.9),
        activeBg: isDark
            ? mixHexColors(primary, shell.surfaceBg, 0.75)
            : mixHexColors(primary, "#ffffff", 0.8),
    };
}

export function resolveThemeRegistryKey(candidate, fallback = "bootstrap") {
    const normalizedCandidate = themeAliases[candidate] || candidate;
    const normalizedFallback = themeAliases[fallback] || fallback;

    if (normalizedCandidate && themeRegistry[normalizedCandidate]) return normalizedCandidate;
    if (normalizedFallback && themeRegistry[normalizedFallback]) return normalizedFallback;
    return Object.keys(themeRegistry)[0];
}

export const themeRegistry = {
    bootstrap: {
        key: "bootstrap",
        appearance: "standard",
        name: "Bootstrap",
        nameKey: "theme.name.bootstrap",
        type: "style",
        modes: ["light", "dark"],
        description: "Bootstrap classic blue shell",
        descriptionKey: "theme.desc.bootstrap",
        colors: {
            light: {
                primary: "#0d6efd",
                headerBg: "#0d6efd",
                headerText: "#ffffff",
                pageBg: "#f8f9fa",
                surfaceBg: "#ffffff",
                asideBg: "#f2f4f7",
                textColor: "#212529",
                mutedText: "#6c757d",
                borderColor: "#dee2e6",
                hoverBg: "#e7f1ff",
                activeBg: "#cfe2ff",
            },
            dark: {
                primary: "#3d8bfd",
                headerBg: "#3d8bfd",
                headerText: "#ffffff",
                pageBg: "#212529",
                surfaceBg: "#2b3035",
                asideBg: "#1a1f24",
                textColor: "#dee2e6",
                mutedText: "#6c757d",
                borderColor: "#495057",
                hoverBg: "#2a3440",
                activeBg: "#2a3a50",
            },
        },
    },
    wechat: {
        key: "wechat",
        appearance: "standard",
        name: "微信键盘",
        nameKey: "theme.name.wechat",
        type: "style",
        modes: ["light", "dark"],
        description: "Clean green desktop shell",
        descriptionKey: "theme.desc.wechat",
        colors: {
            light: {
                primary: "#07c160",
                headerBg: "#07c160",
                headerText: "#ffffff",
                pageBg: "#f7f7f7",
                surfaceBg: "#ffffff",
                asideBg: "#f2f8f4",
                textColor: "#191919",
                mutedText: "#999999",
                borderColor: "#e0e0e0",
                hoverBg: "#e8f8ee",
                activeBg: "#d0f0dd",
            },
            dark: {
                primary: "#07c160",
                headerBg: "#07c160",
                headerText: "#ffffff",
                pageBg: "#111111",
                surfaceBg: "#1c1c1e",
                asideBg: "#142218",
                textColor: "#e5e5e5",
                mutedText: "#666666",
                borderColor: "#333333",
                hoverBg: "#1a2e22",
                activeBg: "#1e3a28",
            },
        },
    },
    orange: {
        key: "orange",
        appearance: "standard",
        name: "泡泡橙",
        nameKey: "theme.name.orange",
        type: "basic",
        modes: ["light", "dark"],
        description: "Warm orange basic palette",
        descriptionKey: "theme.desc.orange",
        colors: {
            light: { primary: "#ffa500" },
            dark: { primary: "#ffb347" },
        },
    },
    cherryRed: {
        key: "cherryRed",
        appearance: "standard",
        name: "樱桃红",
        nameKey: "theme.name.cherryRed",
        type: "basic",
        modes: ["light", "dark"],
        description: "Cherry red basic palette",
        descriptionKey: "theme.desc.cherryRed",
        colors: {
            light: { primary: "#d81b60" },
            dark: { primary: "#d81b60" },
        },
    },
    photoshop: {
        key: "photoshop",
        appearance: "photoshop-cs3",
        name: "Photoshop CS3",
        nameKey: "theme.name.photoshop",
        type: "style",
        modes: ["light", "dark"],
        description: "Adobe CS3-inspired warm gray desktop shell",
        descriptionKey: "theme.desc.photoshop",
        colors: {
            light: {
                primary: "#6d6d68",
                primaryLight3: "#84847d",
                primaryDark2: "#585853",
                headerBg: "#d3d3ce",
                headerText: "#2a2a27",
                pageBg: "#d5d5d0",
                surfaceBg: "#e8e8e3",
                surfaceGradientStart: "#f1f1ef",
                surfaceGradientEnd: "#c7c7c3",
                asideBg: "#dcdcd7",
                workspaceBg: "#656565",
                controlBg: "#ddddda",
                controlBgRaised: "#f1f1ef",
                controlBgSunken: "#d0d0cb",
                asideText: "#32322f",
                textColor: "#3b3b37",
                mutedText: "#555550",
                borderColor: "#afb0aa",
                borderLight: "#fcfcfa",
                borderDark: "#91928c",
                hoverBg: "#d6d6d1",
                activeBg: "#b9b9b3",
                insetHighlight: "rgba(255,255,255,0.82)",
                insetShadow: "rgba(83,83,78,0.22)",
            },
            dark: {
                primary: "#6f8795",
                primaryLight3: "#879eab",
                primaryDark2: "#5b717d",
                headerBg: "#4d4d49",
                headerText: "#f3f3f1",
                pageBg: "#3d3d39",
                surfaceBg: "#4a4a46",
                surfaceGradientStart: "#5b5b56",
                surfaceGradientEnd: "#40403c",
                asideBg: "#43433f",
                workspaceBg: "#2c2c29",
                controlBg: "#4f4f4b",
                controlBgRaised: "#5c5c57",
                controlBgSunken: "#3d3d39",
                asideText: "#ebebe7",
                textColor: "#ecece8",
                mutedText: "#b9b9b3",
                borderColor: "#666761",
                borderLight: "#73746e",
                borderDark: "#232321",
                hoverBg: "#5a5a55",
                activeBg: "#696963",
                insetHighlight: "rgba(255,255,255,0.08)",
                insetShadow: "rgba(0,0,0,0.35)",
            },
        },
    },
};

function mergeShellTokens(shell, themeColors) {
    return {
        primary: themeColors.primary || shell.primary,
        pageBg: themeColors.pageBg || shell.pageBg,
        surfaceBg: themeColors.surfaceBg || shell.surfaceBg,
        asideBg: themeColors.asideBg || shell.asideBg,
        workspaceBg: themeColors.workspaceBg || themeColors.pageBg || shell.workspaceBg,
        controlBg: themeColors.controlBg || themeColors.surfaceBg || shell.controlBg,
        controlBgRaised: themeColors.controlBgRaised || themeColors.surfaceBg || shell.controlBgRaised,
        controlBgSunken: themeColors.controlBgSunken || themeColors.asideBg || shell.controlBgSunken,
        asideText: themeColors.asideText || shell.asideText || themeColors.textColor || shell.textColor,
        textColor: themeColors.textColor || shell.textColor,
        mutedText: themeColors.mutedText || shell.mutedText,
        borderColor: themeColors.borderColor || shell.borderColor,
        borderLight: themeColors.borderLight || shell.borderLight,
        borderDark: themeColors.borderDark || shell.borderDark,
        hoverBg: themeColors.hoverBg || shell.hoverBg,
        activeBg: themeColors.activeBg || shell.activeBg,
        headerBg: themeColors.headerBg || themeColors.primary || themeColors.surfaceBg || shell.headerBg || shell.primary,
        headerText: themeColors.headerText || (themeColors.headerBg || themeColors.primary ? "#ffffff" : null) || themeColors.textColor || shell.headerText || shell.textColor,
        surfaceGradientStart: themeColors.surfaceGradientStart || shell.surfaceGradientStart,
        surfaceGradientEnd: themeColors.surfaceGradientEnd || shell.surfaceGradientEnd,
        insetHighlight: themeColors.insetHighlight || shell.insetHighlight,
        insetShadow: themeColors.insetShadow || shell.insetShadow,
        primaryLight3: themeColors.primaryLight3,
        primaryDark2: themeColors.primaryDark2,
    };
}

export function normalizeThemeTokens(themeConfig, mode) {
    const safeThemeConfig = themeConfig || Object.values(themeRegistry)[0];
    const shell = systemShell[mode] || systemShell.light;
    const themeColors = safeThemeConfig?.colors?.[mode] || safeThemeConfig?.colors?.light || {};

    if (safeThemeConfig?.type === "basic") {
        return mergeShellTokens(shell, buildBasicThemeShellTokens(shell, themeColors, mode));
    }

    return mergeShellTokens(shell, themeColors);
}

export function applyThemeToDocument(tokens, mode, family = "default", appearance = "standard") {
    const root = document.documentElement;
    const primaryScale = buildPrimaryScale(tokens);

    root.classList.toggle("dark", mode === "dark");
    root.dataset.themeFamily = family;
    root.dataset.themeMode = mode;
    root.dataset.themeAppearance = appearance;

    root.style.setProperty("--theme-primary", tokens.primary);
    root.style.setProperty("--theme-page-bg", tokens.pageBg);
    root.style.setProperty("--theme-surface-bg", tokens.surfaceBg);
    root.style.setProperty("--theme-aside-bg", tokens.asideBg);
    root.style.setProperty("--theme-workspace-bg", tokens.workspaceBg);
    root.style.setProperty("--theme-control-bg", tokens.controlBg);
    root.style.setProperty("--theme-control-bg-raised", tokens.controlBgRaised);
    root.style.setProperty("--theme-control-bg-sunken", tokens.controlBgSunken);
    root.style.setProperty("--theme-text-color", tokens.textColor);
    root.style.setProperty("--theme-muted-text", tokens.mutedText);
    root.style.setProperty("--theme-border-color", tokens.borderColor);
    root.style.setProperty("--theme-border-light", tokens.borderLight);
    root.style.setProperty("--theme-border-dark", tokens.borderDark);
    root.style.setProperty("--theme-hover-bg", tokens.hoverBg);
    root.style.setProperty("--theme-active-bg", tokens.activeBg);
    root.style.setProperty("--theme-header-bg", tokens.headerBg);
    root.style.setProperty("--theme-header-text", tokens.headerText);
    root.style.setProperty("--theme-aside-text", tokens.asideText);
    root.style.setProperty("--theme-surface-gradient-start", tokens.surfaceGradientStart);
    root.style.setProperty("--theme-surface-gradient-end", tokens.surfaceGradientEnd);
    root.style.setProperty("--theme-inset-highlight", tokens.insetHighlight);
    root.style.setProperty("--theme-inset-shadow", tokens.insetShadow);

    root.style.setProperty("--el-color-primary", primaryScale.primary);
    root.style.setProperty("--el-color-primary-rgb", primaryScale.primaryRgb);
    for (let level = 1; level <= 9; level += 1) {
        root.style.setProperty(`--el-color-primary-light-${level}`, primaryScale.primaryLightColors[level]);
    }
    root.style.setProperty("--el-color-primary-dark-2", primaryScale.primaryDark2);

    root.style.setProperty("--el-bg-color", tokens.surfaceBg);
    root.style.setProperty("--el-bg-color-page", tokens.pageBg);
    root.style.setProperty("--el-fill-color-light", tokens.hoverBg);
    root.style.setProperty("--el-text-color-primary", tokens.textColor);
    root.style.setProperty("--el-text-color-regular", tokens.textColor);
    root.style.setProperty("--el-text-color-secondary", tokens.mutedText);
    root.style.setProperty("--el-border-color", tokens.borderColor);

    if (appearance === "photoshop-cs3") {
        root.style.setProperty("--el-bg-color-overlay", tokens.controlBgRaised);
        root.style.setProperty("--el-fill-color", tokens.controlBg);
        root.style.setProperty("--el-fill-color-blank", tokens.controlBgRaised);
        root.style.setProperty("--el-border-color-light", tokens.borderLight);
        root.style.setProperty("--el-border-color-lighter", tokens.borderLight);
        root.style.setProperty("--el-border-color-dark", tokens.borderDark);
        root.style.setProperty("--el-mask-color", "rgba(0, 0, 0, 0.35)");
        root.style.setProperty("--el-box-shadow-light", `inset 1px 1px 0 ${tokens.insetHighlight}, inset -1px -1px 0 ${tokens.insetShadow}`);
        root.style.setProperty("--el-box-shadow", `0 0 0 1px ${tokens.borderDark}, inset 1px 1px 0 ${tokens.insetHighlight}`);
        root.style.setProperty("--el-disabled-bg-color", tokens.controlBgSunken);
    } else {
        root.style.removeProperty("--el-bg-color-overlay");
        root.style.removeProperty("--el-fill-color");
        root.style.removeProperty("--el-fill-color-blank");
        root.style.setProperty("--el-border-color-light", tokens.borderColor);
        root.style.setProperty("--el-border-color-lighter", tokens.borderColor);
        root.style.setProperty("--el-border-color-dark", tokens.borderColor);
        root.style.removeProperty("--el-mask-color");
        root.style.removeProperty("--el-box-shadow-light");
        root.style.removeProperty("--el-box-shadow");
        root.style.removeProperty("--el-disabled-bg-color");
    }

    root.style.setProperty("--el-disabled-text-color", tokens.mutedText);
}
