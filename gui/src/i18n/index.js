import { createI18n } from "vue-i18n";
import { supportedLanguages, getDefaultLocale } from "@/i18n/languages.js";
import zhCN from "@/i18n/lang/zh_CN.js";
import enUS from "@/i18n/lang/en_US.js";
// 配置项 label / 校验文案由后端 schema 下发 i18n key，翻译随 Langues 文件同步生成，
// 见 scripts/sync_config_i18n.py。
import configZhCN from "@/i18n/lang/config_zh_CN.js";
import configEnUS from "@/i18n/lang/config_en_US.js";

const messages = {
    zh_CN: { ...zhCN, ...configZhCN },
    en_US: { ...enUS, ...configEnUS },
};

const defaultLocale = getDefaultLocale();

const i18n = createI18n({
    legacy: false,
    locale: defaultLocale,
    fallbackLocale: supportedLanguages[0]?.locale || "zh_CN",
    messages,
});

export default i18n;
