/**
 * 支持的语言配置
 *
 * 新增语言时只需：
 *   1. 在 lang/ 下创建 {locale}.js 翻译文件
 *   2. 在下方 supportedLanguages 数组中添加一条
 *   3. 在 i18n/index.js 中 import 并注册到 messages
 *
 * @example
 *   新增日语（ja_JP）：
 *     lang/ja_JP.js  ← 翻译文件
 *     languages.js   ← { locale: 'ja_JP', label: '日本語' }
 *     index.js       ← import jaJP from '@/i18n/lang/ja_JP.js'
 *                       messages: { ... ja_JP: jaJP }
 */

export const supportedLanguages = [
    { locale: "zh_CN", label: "中文", short: "中" },
    { locale: "en_US", label: "English", short: "EN" },
];

/** 获取所有支持的 locale 列表 */
export function supportedLocales() {
    return supportedLanguages.map((l) => l.locale);
}

/** 获取默认语言（优先使用 .env 配置） */
export function getDefaultLocale() {
    const envLang = import.meta.env.VITE_DEFAULT_LANG;
    const locales = supportedLocales();
    if (envLang && locales.includes(envLang)) {
        return envLang;
    }
    return locales[0] || "zh_CN";
}
