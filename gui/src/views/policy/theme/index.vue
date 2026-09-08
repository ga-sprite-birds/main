<template>
  <div class="page-container page-container--comfortable">
    <div class="theme-page">
      <h2 class="page-title">{{ $t("theme.pageTitle") }}</h2>
      <p class="page-desc">{{ $t("theme.pageDesc") }}</p>

      <el-card class="theme-card-section" shadow="hover">
        <template #header>
          <span class="card-title">{{ $t("theme.family") }}</span>
        </template>

        <div class="theme-grid">
          <div
            v-for="theme in themeStore.availableThemes"
            :key="theme.key"
            class="theme-item"
            :class="{ active: themeStore.themeFamily === theme.key }"
            @click="themeStore.setThemeFamily(theme.key)"
          >
            <div class="theme-color-bar" :style="{ background: theme.previewColor }" />
            <div class="theme-item-info">
              <div class="theme-item-name">{{ theme.name }}</div>
              <el-tag :type="theme.type === 'basic' ? 'info' : 'warning'" size="small">
                {{ theme.type === "basic" ? $t("theme.basic") : $t("theme.style") }}
              </el-tag>
            </div>
            <div v-if="themeStore.themeFamily === theme.key" class="theme-selected-badge">
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="theme-card-section" shadow="hover">
        <template #header>
          <span class="card-title">{{ $t("theme.mode") }}</span>
        </template>

        <div class="mode-preview">
          <div
            class="mode-option"
            :class="{ active: themeStore.themeMode === 'system' }"
            @click="themeStore.setThemeMode('system')"
          >
            <div class="mode-visual mode-system">
              <div class="mode-visual-header" :style="{ background: systemHeaderBg }" />
              <div class="mode-visual-body">
                <div class="mode-visual-sidebar" :style="{ background: systemSidebarBg }" />
                <div class="mode-visual-content" :style="{ background: systemContentBg }" />
              </div>
            </div>
            <div class="mode-label">
              <el-icon><Monitor /></el-icon>
              {{ $t("theme.system") }}
            </div>
          </div>

          <div
            class="mode-option"
            :class="{ active: themeStore.themeMode === 'light' }"
            @click="themeStore.setThemeMode('light')"
          >
            <div class="mode-visual mode-light">
              <div class="mode-visual-header" :style="{ background: lightHeaderBg }" />
              <div class="mode-visual-body">
                <div class="mode-visual-sidebar" :style="{ background: lightSidebarBg }" />
                <div class="mode-visual-content" :style="{ background: lightContentBg }" />
              </div>
            </div>
            <div class="mode-label">
              <el-icon><Sunny /></el-icon>
              {{ $t("theme.light") }}
            </div>
          </div>

          <div
            class="mode-option"
            :class="{ active: themeStore.themeMode === 'dark' }"
            @click="themeStore.setThemeMode('dark')"
          >
            <div class="mode-visual mode-dark">
              <div class="mode-visual-header" :style="{ background: darkHeaderBg }" />
              <div class="mode-visual-body">
                <div class="mode-visual-sidebar" :style="{ background: darkSidebarBg }" />
                <div class="mode-visual-content" :style="{ background: darkContentBg }" />
              </div>
            </div>
            <div class="mode-label">
              <el-icon><Moon /></el-icon>
              {{ $t("theme.dark") }}
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="theme-card-section" shadow="hover">
        <template #header>
          <span class="card-title">{{ $t("theme.currentTokens") }}</span>
        </template>

        <div class="token-list">
          <div
            v-for="(value, key) in displayTokens"
            :key="key"
            class="token-item"
          >
            <div class="token-color-preview" :style="{ background: value }" />
            <div class="token-key">{{ key }}</div>
            <div class="token-value">{{ value }}</div>
          </div>
        </div>
      </el-card>

      <div class="theme-actions">
        <el-button type="danger" plain @click="themeStore.resetTheme()">
          <el-icon><Refresh /></el-icon>
          {{ $t("theme.reset") }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { useThemeStore } from "@/store/modules/theme.js"
import { normalizeThemeTokens } from "@/assets/styles/theme.js"
import { Check, Sunny, Moon, Refresh, Monitor } from "@element-plus/icons-vue"

const themeStore = useThemeStore()

const lightTokens = computed(() => normalizeThemeTokens(themeStore.currentThemeConfig, "light"))
const darkTokens = computed(() => normalizeThemeTokens(themeStore.currentThemeConfig, "dark"))
const lightHeaderBg = computed(() => lightTokens.value.headerBg)
const lightSidebarBg = computed(() => lightTokens.value.asideBg)
const lightContentBg = computed(() => lightTokens.value.pageBg)
const darkHeaderBg = computed(() => darkTokens.value.headerBg)
const darkSidebarBg = computed(() => darkTokens.value.asideBg)
const darkContentBg = computed(() => darkTokens.value.pageBg)
const systemHeaderBg = computed(() => `linear-gradient(90deg, ${lightHeaderBg.value} 0 50%, ${darkHeaderBg.value} 50% 100%)`)
const systemSidebarBg = computed(() => `linear-gradient(180deg, ${lightSidebarBg.value} 0 50%, ${darkSidebarBg.value} 50% 100%)`)
const systemContentBg = computed(() => `linear-gradient(180deg, ${lightContentBg.value} 0 50%, ${darkContentBg.value} 50% 100%)`)

const displayTokens = computed(() => {
  const tokens = themeStore.themeTokens
  const result = {}
  for (const [key, value] of Object.entries(tokens)) {
    if (typeof value === "string" && value.startsWith("#")) {
      result[key] = value
    }
  }
  return result
})
</script>

<style scoped>
.theme-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--theme-text-color);
  margin-bottom: 8px;
}

.page-desc {
  color: var(--theme-text-color);
  opacity: 0.65;
  font-size: 14px;
  margin-bottom: 24px;
}

.theme-card-section {
  margin-bottom: 20px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--theme-text-color);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.theme-item {
  position: relative;
  border: 2px solid var(--theme-border-color);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
}

.theme-item:hover {
  border-color: var(--theme-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.theme-item.active {
  border-color: var(--theme-primary);
  box-shadow: 0 0 0 2px var(--theme-primary);
}

.theme-color-bar {
  height: 60px;
}

.theme-item-info {
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.theme-item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--theme-text-color);
}

.theme-selected-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--theme-primary);
  color: var(--theme-header-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.mode-preview {
  display: flex;
  gap: 24px;
}

.mode-option {
  flex: 1;
  cursor: pointer;
  border: 2px solid var(--theme-border-color);
  border-radius: 10px;
  padding: 16px;
  transition: all 0.25s ease;
}

.mode-option:hover {
  border-color: var(--theme-primary);
}

.mode-option.active {
  border-color: var(--theme-primary);
  background-color: var(--theme-hover-bg);
}

.mode-visual {
  height: 100px;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
}

.mode-visual-header {
  height: 20px;
}

.mode-visual-body {
  height: 80px;
  display: flex;
}

.mode-visual-sidebar {
  width: 30%;
}

.mode-visual-content {
  width: 70%;
}

.mode-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--theme-text-color);
}

.token-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 8px;
}

.token-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--theme-page-bg);
  border-radius: 6px;
  font-size: 13px;
}

.token-color-preview {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--theme-border-color);
  flex-shrink: 0;
}

.token-key {
  font-weight: 500;
  color: var(--theme-text-color);
  min-width: 80px;
}

.token-value {
  color: var(--theme-muted-text);
  font-family: "Menlo", "Monaco", monospace;
  font-size: 12px;
}

.theme-actions {
  text-align: center;
  margin-top: 32px;
}
</style>
