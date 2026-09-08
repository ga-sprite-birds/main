import { createI18n } from "vue-i18n";
import { supportedLanguages, getDefaultLocale } from "@/i18n/languages.js";
import zhCN from "@/i18n/lang/zh_CN.js";
import enUS from "@/i18n/lang/en_US.js";

const messages = {
    zh_CN: zhCN,
    en_US: enUS,
};

const defaultLocale = getDefaultLocale();

const i18n = createI18n({
    legacy: false,
    locale: defaultLocale,
    fallbackLocale: supportedLanguages[0]?.locale || "zh_CN",
    messages,
});

export default i18n;
