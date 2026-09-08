<template>
  <el-drawer
    v-model="visible"
    :title="$t('theme.settings')"
    direction="rtl"
    size="380px"
    @closed="handleClose"
  >
    <div class="theme-settings">
      <div class="setting-section">
        <h3 class="setting-title">{{ $t('theme.mode') }}</h3>
        <div class="mode-switch">
          <el-button
            :type="themeStore.themeMode === 'system' ? 'primary' : 'default'"
            class="mode-btn"
            @click="themeStore.setThemeMode('system')"
          >
            <el-icon><Monitor /></el-icon>
            {{ $t('theme.system') }}
          </el-button>
          <el-button
            :type="themeStore.themeMode === 'light' ? 'primary' : 'default'"
            class="mode-btn"
            @click="themeStore.setThemeMode('light')"
          >
            <el-icon><Sunny /></el-icon>
            {{ $t('theme.light') }}
          </el-button>
          <el-button
            :type="themeStore.themeMode === 'dark' ? 'primary' : 'default'"
            class="mode-btn"
            @click="themeStore.setThemeMode('dark')"
          >
            <el-icon><Moon /></el-icon>
            {{ $t('theme.dark') }}
          </el-button>
        </div>
      </div>

      <div class="setting-section">
        <h3 class="setting-title">{{ $t('theme.family') }}</h3>
        <div class="theme-list">
          <div
            v-for="theme in themeStore.availableThemes"
            :key="theme.key"
            class="theme-card"
            :class="{ active: themeStore.themeFamily === theme.key }"
            @click="themeStore.setThemeFamily(theme.key)"
          >
            <div
              class="theme-preview"
              :style="{ backgroundColor: theme.previewColor }"
            />
            <div class="theme-info">
              <div class="theme-name">{{ theme.name }}</div>
              <div class="theme-type">
                {{ theme.type === 'basic' ? $t('theme.basic') : $t('theme.style') }}
              </div>
            </div>
            <el-icon v-if="themeStore.themeFamily === theme.key" class="theme-checked">
              <Check />
            </el-icon>
          </div>
        </div>
      </div>

      <div class="setting-section">
        <h3 class="setting-title">{{ $t('theme.description') }}</h3>
        <p class="theme-desc-text">
          {{ currentThemeDesc }}
        </p>
      </div>

      <div class="setting-section">
        <el-button class="reset-btn" @click="handleReset">
          <el-icon><Refresh /></el-icon>
          {{ $t('theme.reset') }}
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from "vue"
import { useThemeStore } from "@/store/modules/theme.js"
import i18n from "@/i18n/index.js"
import { Sunny, Moon, Check, Refresh, Monitor } from "@element-plus/icons-vue"

const props = defineProps({
  visible: Boolean,
})

const emit = defineEmits(["update:visible"])

const themeStore = useThemeStore()

const visible = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
})

const currentThemeDesc = computed(() => {
  const config = themeStore.currentThemeConfig
  const key = config.descriptionKey
  return key ? i18n.global.t(key) : config.description || ""
})

function handleClose() {}

function handleReset() {
  themeStore.resetTheme()
}
</script>

<style scoped>
.theme-settings {
  padding: 0 4px;
}

.setting-section {
  margin-bottom: 28px;
}

.setting-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-text-color);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--theme-border-color);
}

.mode-switch {
  display: flex;
  gap: 12px;
}

.mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 48px;
  font-size: 14px;
}

.theme-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.theme-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 2px solid var(--theme-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
}

.theme-card:hover {
  border-color: var(--theme-primary);
  background-color: var(--theme-hover-bg);
}

.theme-card.active {
  border-color: var(--theme-primary);
  background-color: var(--theme-hover-bg);
}

.theme-preview {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  flex-shrink: 0;
}

.theme-info {
  flex: 1;
  min-width: 0;
}

.theme-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--theme-text-color);
}

.theme-type {
  font-size: 12px;
  color: var(--theme-muted-text);
  margin-top: 2px;
}

.theme-checked {
  color: var(--theme-primary);
  font-size: 18px;
}

.theme-desc-text {
  font-size: 13px;
  color: var(--theme-muted-text);
  line-height: 1.6;
}

.reset-btn {
  width: 100%;
}
</style>
