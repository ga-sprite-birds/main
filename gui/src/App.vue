<template>
  <el-config-provider :locale="elLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import zhCn from "element-plus/dist/locale/zh-cn.mjs"
import en from "element-plus/dist/locale/en.mjs"

const { locale } = useI18n({ useScope: "global" })
const elLocaleMap = { zh_CN: zhCn, en_US: en }
const elLocale = computed(() => elLocaleMap[locale.value] || zhCn)
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}
</style>
