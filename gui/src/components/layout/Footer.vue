<template>
  <el-footer
    class="layout-footer"
    :style="{ height: footerHeight + 'px' }"
  >
    <div class="footer-content">
      <div class="footer-line">
        {{ appTitle }} {{ $t("footer.managementSystem") }}
        <span v-if="buildVersion" class="footer-version">build-{{ buildVersion }}</span>
      </div>
      <div class="footer-line">
        &copy;{{ currentYear }} {{ companyName }} Corporation. All Rights Reserved.
      </div>
    </div>
  </el-footer>
</template>

<script setup>
const appTitle = import.meta.env.VITE_APP_TITLE || "GA Sprite Birds"
const companyName = import.meta.env.VITE_COMPANY_NAME || appTitle
const buildVersion = import.meta.env.VITE_APP_BUILD_VERSION || ""
const currentYear = new Date().getFullYear()
const footerHeight = 50
</script>

<style scoped>
.layout-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  background: var(--theme-surface-bg);
  border-top: 1px solid var(--theme-border-color);
  color: var(--theme-muted-text);
  font-size: 12px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.footer-content {
  text-align: right;
  line-height: 1.6;
}

.footer-version {
  margin-left: 6px;
  color: var(--theme-muted-text);
}
</style>
