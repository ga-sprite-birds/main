<template>
  <el-container class="policy-layout">
    <!-- ── Header ────────────────────────────────────────── -->
    <Header
      header-fixed
      :sidebar-width="sidebarWidth"
      @open-theme-drawer="themeDrawerVisible = true"
    />

    <el-container class="layout-body">
      <!-- ── Sidebar ──────────────────────────────────────── -->
      <Sidebar
        :collapsed="appStore.sidebarCollapsed"
        :width="sidebarWidth"
        :collapsed-width="sidebarCollapsedWidth"
      />

      <!-- ── Main ──────────────────────────────────────────── -->
      <el-main
        class="layout-main"
        :class="{ 'layout-main-classic': isClassicTheme }"
        :style="{
          background: mainBackground,
          transition: 'background-color 0.3s ease',
        }"
      >
        <!-- 二级导航/TAB 预留区 -->
        <div v-if="route.meta?.showTabs" class="layout-tabs">
          <!-- 未来可在此插入 Tab 导航 -->
        </div>

        <!-- 主内容区：遵循“框架背景全宽，页面按场景控宽”原则 -->
        <div class="layout-content-wrapper" :class="{ 'layout-content-wrapper-classic': isClassicTheme }">
          <router-view />
        </div>
      </el-main>
    </el-container>

    <!-- ── Footer ──────────────────────────────────────────── -->
    <Footer />

    <!-- ── 主题设置抽屉 ──────────────────────────────────── -->
    <ThemeSettingsDrawer v-model:visible="themeDrawerVisible" />
  </el-container>
</template>

<script setup>
import { computed, ref } from "vue"
import { useRoute } from "vue-router"
import { useAppStore } from "@/store/modules/app.js"
import { useThemeStore } from "@/store/modules/theme.js"

import Header from "@/components/layout/Header.vue"
import Sidebar from "@/components/layout/Sidebar.vue"
import Footer from "@/components/layout/Footer.vue"
import ThemeSettingsDrawer from "@/components/layout/ThemeSettingsDrawer.vue"

const route = useRoute()
const appStore = useAppStore()
const themeStore = useThemeStore()
const isClassicTheme = computed(() => themeStore.themeAppearance === "photoshop-cs3")
const mainBackground = computed(() => (isClassicTheme.value ? "var(--theme-workspace-bg)" : "var(--theme-page-bg)"))

const themeDrawerVisible = ref(false)

const sidebarWidth = 200
const sidebarCollapsedWidth = 64
</script>

<style scoped>
.policy-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-body {
  flex: 1;
  overflow: hidden;
}

.layout-main {
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.layout-main-classic {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* ── TAB 预留区 ───────────────────────────────────────── */
.layout-tabs {
  flex-shrink: 0;
}

/* ── 主内容区：框架背景全宽，页面按场景控宽 ─────────── */
.layout-content-wrapper {
  flex: 1;
  padding: 20px;
  width: 100%;
}

.layout-content-wrapper-classic {
  padding: 14px;
}

/* 页面按场景选择宽度：列表全宽，表单/详情控宽。 */
.layout-content-wrapper :deep(.page-container) {
  width: 100%;
  margin: 0 auto;
}

.layout-content-wrapper :deep(.page-container--comfortable) {
  max-width: 1200px;
}

.layout-content-wrapper :deep(.page-container--narrow) {
  max-width: 960px;
}

.layout-content-wrapper :deep(.page-container--wide) {
  max-width: 1440px;
}

.layout-content-wrapper :deep(.page-container--fluid) {
  max-width: none;
}
</style>
