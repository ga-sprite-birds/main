<template>
  <el-header
    class="layout-header"
    :class="{ 'header-fixed': headerFixed, 'layout-header-classic': isClassicTheme }"
    :style="{
      height: headerHeight + 'px',
      background: headerBg,
      color: headerTextColor,
      zIndex: 100,
    }"
  >
    <!-- 左侧 Logo 区 -->
    <div class="header-left" :class="{ 'header-left-classic': isClassicTheme }" :style="{ width: sidebarWidth + 'px' }">
      <span class="logo-text">{{ appTitle }}</span>
    </div>

    <!-- 右侧操作区 -->
    <div class="header-right" :class="{ 'header-right-classic': isClassicTheme }">
      <div class="header-actions">
        <!-- 明暗模式切换 -->
        <el-tooltip :content="isDark ? $t('theme.switchToLight') : $t('theme.switchToDark')" placement="bottom">
          <el-button
            class="theme-toggle-btn"
            :icon="isDark ? Sunny : Moon"
            circle
            @click="themeStore.toggleThemeMode()"
          />
        </el-tooltip>

        <!-- 主题设置入口 -->
        <el-tooltip :content="$t('theme.settings')" placement="bottom">
          <el-button
            class="theme-toggle-btn"
            :icon="Setting"
            circle
            @click="emit('openThemeDrawer')"
          />
        </el-tooltip>

        <!-- 语言切换 -->
        <el-dropdown trigger="click" @command="switchLang">
          <el-button
            class="lang-toggle-btn"
            circle
            :style="{ color: headerTextColor }"
          >
            <span class="lang-short">{{ currentLangShort }}</span>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="lang in supportedLanguages"
                :key="lang.locale"
                :command="lang.locale"
                :disabled="lang.locale === currentLocale"
              >
                {{ lang.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-tag class="api-chip" effect="plain">FastAPI</el-tag>
      </div>
    </div>
  </el-header>
</template>

<script setup>
import { computed } from "vue"
import { useThemeStore } from "@/store/modules/theme.js"
import { useI18n } from "vue-i18n"
import { supportedLanguages } from "@/i18n/languages.js"
import { Setting, Sunny, Moon } from "@element-plus/icons-vue"

const emit = defineEmits(["openThemeDrawer"])

const props = defineProps({
  headerFixed: { type: Boolean, default: true },
  sidebarWidth: { type: Number, default: 200 },
})

const themeStore = useThemeStore()
const { locale } = useI18n({ useScope: "global" })

const appTitle = import.meta.env.VITE_APP_TITLE || "GA Sprite Birds"
const headerHeight = 60
const isDark = computed(() => themeStore.isDark)
const isClassicTheme = computed(() => themeStore.themeAppearance === "photoshop-cs3")

// Header 统一消费归一化后的壳层 token
const headerBg = computed(() => "var(--theme-header-bg)")
const headerTextColor = computed(() => "var(--theme-header-text)")

// ── 多语言 ────────────────────────────────────────────────
const currentLocale = computed(() => locale.value)
const currentLangShort = computed(() => {
  const found = supportedLanguages.find(l => l.locale === locale.value)
  return found ? found.short : locale.value
})

function switchLang(newLocale) {
  locale.value = newLocale
}
</script>
<style scoped>
.layout-header {
  display: flex;
  align-items: center;
  padding: 0 0 0 0;
  transition: background-color 0.3s ease, color 0.3s ease;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-fixed {
  position: sticky;
  top: 0;
}

.header-left {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: width 0.3s;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  min-width: 0;
}

.layout-header-classic {
  border-bottom: 1px solid var(--theme-border-dark);
  box-shadow: inset 0 1px 0 var(--theme-border-light);
}

.header-left-classic {
  height: 100%;
  background: linear-gradient(to bottom, var(--theme-surface-gradient-start), var(--theme-surface-gradient-end));
  border-right: 1px solid var(--theme-border-dark);
  box-shadow: inset -1px 0 0 var(--theme-border-light);
}

.header-right-classic {
  background: linear-gradient(to bottom, var(--theme-surface-gradient-start), var(--theme-surface-gradient-end));
}

.header-left-classic .logo-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--theme-text-color);
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.theme-toggle-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.15);
  --el-button-hover-border-color: transparent;
  --el-button-text-color: inherit;
  --el-button-hover-text-color: inherit;
}

.lang-toggle-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.15);
  --el-button-hover-border-color: transparent;
  --el-button-text-color: inherit;
  --el-button-hover-text-color: inherit;
  font-size: 13px;
  font-weight: 700;
  width: 32px;
  height: 32px;
  padding: 0;
}

.api-chip {
  border-color: rgba(255, 255, 255, 0.35);
  color: inherit;
  background: rgba(255, 255, 255, 0.12);
}

.layout-header-classic .theme-toggle-btn,
.layout-header-classic .lang-toggle-btn {
  --el-button-bg-color: var(--theme-control-bg);
  --el-button-border-color: var(--theme-border-dark);
  --el-button-hover-bg-color: var(--theme-hover-bg);
  --el-button-hover-border-color: var(--theme-border-dark);
  --el-button-text-color: var(--theme-text-color);
  --el-button-hover-text-color: var(--theme-text-color);
  box-shadow: inset 1px 1px 0 var(--theme-border-light);
}

.lang-short {
  font-size: 13px;
  letter-spacing: 0;
  line-height: 1;
}

</style>
