<template>
  <div class="page-container page-container--wide">
    <div class="config-page">
      <div class="page-head">
        <div>
          <h2 class="page-title">{{ $t("configPage.title") }}</h2>
          <p class="page-desc">{{ $t("configPage.desc") }}</p>
        </div>
        <div class="page-actions">
          <el-button :loading="loading" @click="fetchData()">
            {{ $t("configPage.refresh") }}
          </el-button>
          <el-button
            :disabled="!dirtyKeys.length || saving || loading"
            @click="resetAll"
          >
            {{ $t("configPage.resetAll") }}
          </el-button>
          <el-button
            type="primary"
            :loading="saving"
            :disabled="!dirtyKeys.length || loading"
            @click="save"
          >
            {{ $t("configPage.save") }}
            <span v-if="dirtyKeys.length" class="dirty-count">
              ({{ dirtyKeys.length }})
            </span>
          </el-button>
        </div>
      </div>

      <el-alert
        class="scope-alert"
        type="info"
        :closable="false"
        show-icon
        :title="$t('configPage.onlyNewTasks')"
      />

      <el-alert
        v-if="loadError"
        class="scope-alert"
        type="error"
        :closable="false"
        show-icon
        :title="loadError"
      />

      <el-skeleton v-if="loading && !sections.length" :rows="8" animated />

      <div v-else class="config-body">
        <el-menu
          class="section-nav"
          :default-active="activeSection"
          :collapse="false"
          @select="selectSection"
        >
          <el-menu-item
            v-for="section in sections"
            :key="section.section_key"
            :index="section.section_key"
          >
            <el-icon>
              <component :is="sectionIcon(section.section_key)" />
            </el-icon>
            <template #title>
              <span class="nav-title">{{ $t(section.title_i18n) }}</span>
              <el-tag
                v-if="sectionDirtyCount(section)"
                size="small"
                type="warning"
                effect="plain"
                class="nav-tag"
              >
                {{ sectionDirtyCount(section) }}
              </el-tag>
              <el-tag
                v-else-if="sectionOverriddenCount(section)"
                size="small"
                type="info"
                effect="plain"
                class="nav-tag"
              >
                {{ sectionOverriddenCount(section) }}
              </el-tag>
            </template>
          </el-menu-item>
        </el-menu>

        <el-card class="section-panel" shadow="never">
          <template #header>
            <div class="panel-head">
              <span class="panel-title">{{ activeSectionTitle }}</span>
              <el-button
                size="small"
                :disabled="saving || !sectionOverriddenCount(activeSectionData)"
                @click="resetSection"
              >
                {{ $t("configPage.resetSection") }}
              </el-button>
            </div>
          </template>

          <el-form v-if="activeSectionData" label-position="top">
            <ConfigField
              v-for="item in activeSectionData.items"
              :key="item.key"
              :item="item"
              :model-value="values[item.key]"
              :voices="voices"
              :class="{ 'field-dirty': isDirty(item.key) }"
              @update:model-value="(value) => updateValue(item.key, value)"
            />
          </el-form>
          <el-empty v-else :description="$t('configPage.emptySection')" />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import {
  ChatDotRound,
  Document,
  Filter,
  FolderOpened,
  MagicStick,
  Microphone,
  Setting,
  User,
} from "@element-plus/icons-vue"

import ConfigField from "./components/ConfigField.vue"
import { systemConfigApi } from "@/api"

const { t, te } = useI18n({ useScope: "global" })
const route = useRoute()
const router = useRouter()

const sections = ref([])
const activeSection = ref("")
const values = reactive({})
const original = reactive({})
const voices = ref([])
const loading = ref(false)
const saving = ref(false)
const loadError = ref("")

const SECTION_ICONS = {
  language: ChatDotRound,
  llm: MagicStick,
  tts: Microphone,
  chapter: Document,
  output: FolderOpened,
  text_preprocessing: Filter,
  character_analysis: User,
}

function sectionIcon(key) {
  return SECTION_ICONS[key] || Setting
}

const activeSectionData = computed(() =>
  sections.value.find((section) => section.section_key === activeSection.value),
)

const activeSectionTitle = computed(() =>
  activeSectionData.value ? t(activeSectionData.value.title_i18n) : "",
)

const dirtyKeys = computed(() =>
  Object.keys(values).filter((key) => !isSame(values[key], original[key])),
)

function isSame(left, right) {
  if (Array.isArray(left) || Array.isArray(right)) {
    return JSON.stringify(left) === JSON.stringify(right)
  }
  return left === right
}

function isDirty(key) {
  if (!(key in values) || !(key in original)) return false
  return !isSame(values[key], original[key])
}

function sectionDirtyCount(section) {
  return section.items.filter((item) => isDirty(item.key)).length
}

function sectionOverriddenCount(section) {
  if (!section) return 0
  return section.items.filter((item) => item.overridden).length
}

function updateValue(key, value) {
  values[key] = value
}

function selectSection(key) {
  activeSection.value = key
  if (route.query.section !== key) {
    router.replace({ path: route.path, query: { ...route.query, section: key } })
  }
}

// 侧边栏每个配置分组都指向 /system/config?section=xxx。
watch(
  () => route.query.section,
  (value) => {
    if (
      typeof value === "string" &&
      sections.value.some((section) => section.section_key === value)
    ) {
      activeSection.value = value
    }
  },
)

function translateMessage(message, fallback) {
  if (typeof message !== "string" || !message) return fallback || ""
  if (message.startsWith("config.") && te(message)) return t(message)
  return message
}

function applyPayload(payload) {
  const list = payload?.sections || []
  sections.value = list
  for (const key of Object.keys(values)) delete values[key]
  for (const key of Object.keys(original)) delete original[key]
  for (const section of list) {
    for (const item of section.items) {
      values[item.key] = Array.isArray(item.value)
        ? [...item.value]
        : item.value
      original[item.key] = Array.isArray(item.value)
        ? [...item.value]
        : item.value
    }
  }
  const querySection = route.query.section
  if (
    typeof querySection === "string" &&
    list.some((section) => section.section_key === querySection)
  ) {
    activeSection.value = querySection
  } else if (
    !list.some((section) => section.section_key === activeSection.value)
  ) {
    activeSection.value = list.length ? list[0].section_key : ""
  }
}

async function fetchData({ silent = false } = {}) {
  loading.value = true
  if (!silent) loadError.value = ""
  try {
    const payload = await systemConfigApi.getSystemConfig()
    applyPayload(payload)
    loadVoices(payload)
  } catch (error) {
    loadError.value = translateMessage(
      error?.message,
      t("configPage.loadFailed"),
    )
  } finally {
    loading.value = false
  }
}

async function loadVoices(payload) {
  const needsVoices = (payload?.sections || []).some((section) =>
    section.items.some((item) => item.type === "dynamic-select"),
  )
  if (!needsVoices || voices.value.length) return
  try {
    const result = await systemConfigApi.getTtsVoices({ silent: true })
    voices.value = Array.isArray(result) ? result : result?.voices || []
  } catch {
    // 引擎离线时音色列表不可用，输入框仍允许手工填写。
    voices.value = []
  }
}

async function save() {
  if (!dirtyKeys.value.length) return
  const payload = {}
  for (const key of dirtyKeys.value) {
    payload[key] = values[key]
  }
  saving.value = true
  try {
    const result = await systemConfigApi.updateSystemConfig(payload)
    if (result?.warning) {
      ElMessage.warning(translateMessage(result.warning))
    }
    ElMessage.success(t("configPage.saveDone"))
    await fetchData({ silent: true })
  } catch (error) {
    const key = error?.data?.key
    const message = translateMessage(
      error?.message,
      t("configPage.saveFailed"),
    )
    ElMessage.error(key ? `${key}: ${message}` : message)
  } finally {
    saving.value = false
  }
}

async function resetSection() {
  if (!activeSectionData.value) return
  try {
    await ElMessageBox.confirm(
      t("configPage.resetSectionConfirm", {
        section: activeSectionTitle.value,
      }),
      t("configPage.resetConfirmTitle"),
      { type: "warning" },
    )
  } catch {
    return
  }
  saving.value = true
  try {
    await systemConfigApi.resetSystemConfig({
      section: activeSection.value,
    })
    ElMessage.success(t("configPage.resetDone"))
    await fetchData({ silent: true })
  } catch (error) {
    ElMessage.error(translateMessage(error?.message, t("configPage.saveFailed")))
  } finally {
    saving.value = false
  }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm(
      t("configPage.resetAllConfirm"),
      t("configPage.resetConfirmTitle"),
      { type: "warning" },
    )
  } catch {
    return
  }
  saving.value = true
  try {
    await systemConfigApi.resetSystemConfig({ all: true })
    ElMessage.success(t("configPage.resetDone"))
    await fetchData({ silent: true })
  } catch (error) {
    ElMessage.error(translateMessage(error?.message, t("configPage.saveFailed")))
  } finally {
    saving.value = false
  }
}

onMounted(() => fetchData())
</script>

<style scoped>
.config-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0 0 6px;
}

.page-desc {
  margin: 0;
  color: var(--theme-muted-text);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dirty-count {
  margin-left: 2px;
  opacity: 0.8;
}

.scope-alert {
  border-radius: 8px;
}

.config-body {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.section-nav {
  width: 220px;
  flex: 0 0 220px;
  border: 1px solid var(--theme-border-color);
  border-radius: 8px;
  padding: 6px 0;
  background: var(--theme-surface-bg);
  position: sticky;
  top: 0;

  /* Element Plus 菜单的悬停/选中底色默认取 primary-light-9（primary 与白色
     90% 混合），深色主题下几乎是纯白；而菜单文字是浅色，于是悬停瞬间变成
     白底白字、整行“消失”。这里统一改用主题语义色，与 Sidebar 保持一致。 */
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--theme-text-color);
  --el-menu-hover-bg-color: var(--theme-hover-bg);
  --el-menu-hover-text-color: var(--theme-text-color);
  --el-menu-active-color: var(--theme-text-color);
  --el-menu-border-color: transparent;
}

.section-nav :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
}

/* 显式给悬停/选中上底色，避免只依赖 EP 默认色板；文字统一用主题正文色，
   因为部分深色主题（如 Photoshop CS3）的 primary 是偏暗的蓝灰，压在
   hover/active 底色上对比度不足，选中态改用左侧强调条来体现。 */
.section-nav :deep(.el-menu-item:hover) {
  background: var(--theme-hover-bg);
  color: var(--theme-text-color);
}

.section-nav :deep(.el-menu-item.is-active) {
  position: relative;
  background: var(--theme-active-bg);
  color: var(--theme-text-color);
  font-weight: 600;
}

.section-nav :deep(.el-menu-item.is-active::before) {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  width: 3px;
  height: 20px;
  border-radius: 0 2px 2px 0;
  transform: translateY(-50%);
  background: var(--theme-primary);
}

.section-nav :deep(.el-menu-item:hover .el-icon),
.section-nav :deep(.el-menu-item.is-active .el-icon) {
  color: inherit;
}

.nav-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-tag {
  margin-left: 6px;
}

.section-panel {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--theme-border-color);
  border-radius: 8px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-title {
  font-weight: 600;
}

.field-dirty :deep(.el-form-item__label) {
  color: var(--el-color-warning);
}

@media (max-width: 900px) {
  .config-body {
    flex-direction: column;
  }

  .section-nav {
    width: 100%;
    flex: none;
    position: static;
  }
}
</style>
