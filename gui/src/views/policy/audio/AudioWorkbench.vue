<template>
  <div class="page-container page-container--wide audio-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">{{ appTitle }}</p>
        <h1>{{ $t("audio.title") }}</h1>
      </div>
      <el-tag :type="serviceReady ? 'success' : 'info'" effect="plain">
        {{ serviceReady ? $t("audio.apiOnline") : $t("audio.apiPending") }}
      </el-tag>
    </section>

    <section class="workspace-grid">
      <div class="panel flow-panel">
        <div class="panel-header">
          <h2>{{ $t("audio.source") }}</h2>
          <el-tag effect="plain">{{ currentStepLabel }}</el-tag>
        </div>

        <el-upload
          drag
          multiple
          class="source-upload"
          :auto-upload="false"
          :disabled="busy || isGenerating"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :accept="'.txt,.md,.pdf'"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="el-upload__text">{{ $t("audio.dropText") }}</div>
        </el-upload>

        <el-form label-position="top" class="option-form">
          <el-form-item :label="$t('audio.outputPath')">
            <el-autocomplete
              v-model="outputPath"
              :fetch-suggestions="fetchOutputPathSuggestions"
              :placeholder="$t('audio.outputPlaceholder')"
              :prefix-icon="FolderOpened"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="voice-label">
                {{ $t("audio.voice") }}
                <a
                  class="voice-preview"
                  href="https://edge-tts.com/zh-CN/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ $t("audio.voicePreview") }}
                </a>
              </span>
            </template>
            <el-select v-model="voice" filterable allow-create default-first-option>
              <el-option
                v-for="item in voiceOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="enableLlm">{{ $t("audio.enableLlm") }}</el-checkbox>
          </el-form-item>
        </el-form>

        <div class="action-row">
          <el-button
            :icon="DocumentChecked"
            :loading="busyAction === 'parse'"
            :disabled="!taskId || busy || isGenerating"
            @click="parseSource"
          >
            {{ $t("audio.parseAction") }}
          </el-button>
        </div>
      </div>

      <div class="panel status-panel">
        <div class="panel-header">
          <h2>{{ $t("audio.progress") }}</h2>
          <el-button :icon="Refresh" circle :disabled="!taskId || busyAction" @click="refreshStatus()" />
        </div>

        <div class="progress-ring">
          <el-progress type="dashboard" :percentage="progressPercent" :status="progressStatus" />
          <div class="progress-copy">
            <strong>{{ statusText }}</strong>
            <span>{{ completedChapters }}/{{ totalChapters }} {{ $t("audio.chapterUnit") }}</span>
          </div>
        </div>

        <el-descriptions :column="1" border class="task-meta">
          <el-descriptions-item :label="$t('audio.taskId')">
            <span class="mono">{{ taskId || "-" }}</span>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('audio.createdAt')">
            {{ formatDate(statusData?.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('audio.finishedAt')">
            {{ formatDate(statusData?.completed_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </section>

    <section class="panel chapter-panel">
      <div class="panel-header">
        <div>
          <h2>{{ $t("audio.chapters") }}</h2>
          <span class="panel-subtitle">{{ $t("audio.chaptersHint") }}</span>
        </div>
        <el-select
          v-model="statusFilter"
          class="status-filter"
          clearable
          :placeholder="$t('audio.filterStatus')"
        >
          <el-option
            v-for="option in statusFilterOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </div>

      <div class="chapter-actions">
        <el-button
          type="primary"
          :icon="VideoPlay"
          :loading="busyAction === 'start'"
          :disabled="!canStartSelected"
          @click="startSelectedChapters"
        >
          {{ $t("audio.startSelected") }}
        </el-button>
        <el-button
          :icon="VideoPause"
          :disabled="!isGenerating || busy"
          @click="pauseGeneration"
        >
          {{ $t("audio.pauseAction") }}
        </el-button>
        <el-button
          type="success"
          plain
          :icon="VideoPlay"
          :disabled="!isPaused || busy"
          @click="resumeGeneration"
        >
          {{ $t("audio.resumeAction") }}
        </el-button>
        <el-button
          type="danger"
          plain
          :icon="Delete"
          :disabled="!canDeleteSelected || busy"
          @click="deleteSelectedChapters"
        >
          {{ $t("audio.deleteAction") }}
        </el-button>
        <el-button :disabled="chapters.length === 0" @click="invertSelection">
          {{ $t("audio.invertSelection") }}
        </el-button>
        <span class="panel-subtitle">
          {{ $t("audio.selectedCount", { count: selectedIndexes.length }) }}
        </span>
      </div>

      <el-empty v-if="chapters.length === 0" :description="$t('audio.emptyChapters')" />
      <el-empty v-else-if="visibleChapters.length === 0" :description="$t('audio.emptyFilteredChapters')" />
      <el-table
        v-else
        ref="chapterTableRef"
        :data="visibleChapters"
        class="chapter-table"
        row-key="index"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="46" reserve-selection />
        <el-table-column prop="index" :label="$t('audio.index')" width="80" />
        <el-table-column prop="title" :label="$t('audio.chapterTitle')" min-width="200" show-overflow-tooltip />
        <el-table-column :label="$t('audio.chapterStatus')" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain">
              {{ mapChapterStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('audio.listen')" min-width="240">
          <template #default="{ row }">
            <audio
              v-if="row.status === 'completed'"
              :key="row.completed_at || row.index"
              controls
              preload="none"
              :src="getChapterAudioUrl(taskId, row.index, row.completed_at)"
            />
            <span v-else class="muted">{{ row.error || $t("audio.waitingAudio") }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('audio.download')" width="110" align="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'completed'"
              :icon="Download"
              circle
              tag="a"
              :href="getChapterAudioUrl(taskId, row.index, row.completed_at)"
              :download="`${row.index}-${row.title || 'chapter'}.mp3`"
            />
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { ElMessage, ElMessageBox } from "element-plus"
import {
  Delete,
  DocumentChecked,
  Download,
  FolderOpened,
  Refresh,
  UploadFilled,
  VideoPause,
  VideoPlay,
} from "@element-plus/icons-vue"
import {
  deleteChapterAudio,
  generateAudio,
  getApiStatus,
  getChapterAudioUrl,
  getTaskStatus,
  parseAudioSource,
  pauseAudio,
  resumeAudio,
  uploadAudioSource,
} from "@/api/audio.js"
import { AUDIO_TASK_STORAGE_KEY, useTaskDisplay } from "@/utils/taskDisplay.js"
import { get as getStoredValue, set as setStoredValue } from "@/utils/storage.js"

const OUTPUT_HISTORY_KEY = "audio_output_paths"
const OUTPUT_HISTORY_LIMIT = 12

const { locale, t } = useI18n({ useScope: "global" })
const { mapStatus, mapChapterStatus, statusTagType, formatDate } = useTaskDisplay()

const appTitle = import.meta.env.VITE_APP_TITLE || "GA Sprite Birds"
const uploadQueue = []
const uploading = ref(false)
const outputPath = ref("")
const voice = ref("zh-CN-YunxiNeural")
const enableLlm = ref(true)
const taskId = ref("")
const statusData = ref(null)
const apiOnline = ref(false)
const busyAction = ref("")
const pollTimer = ref(null)
const chapterTableRef = ref(null)
const selectedIndexes = ref([])
const statusFilter = ref("")
const selectionInitializedFor = ref("")
const TERMINAL_STATUSES = new Set(["parsed", "completed", "failed", "cancelled", "paused"])
let statusRequestId = 0
let pollInFlight = false

const voiceOptions = [
  { label: "云希 - 中文男声", value: "zh-CN-YunxiNeural" },
  { label: "晓晓 - 中文女声", value: "zh-CN-XiaoxiaoNeural" },
  { label: "云扬 - 中文新闻男声", value: "zh-CN-YunyangNeural" },
  { label: "云健 - 中文男声", value: "zh-CN-YunjianNeural" },
  { label: "Jenny - English", value: "en-US-JennyNeural" },
  { label: "Guy - English", value: "en-US-GuyNeural" },
]

const busy = computed(() => Boolean(busyAction.value))
const isGenerating = computed(() => statusData.value?.status === "generating")
const isPaused = computed(() => statusData.value?.status === "paused")
const totalChapters = computed(() => statusData.value?.total_chapters || 0)
const completedChapters = computed(() => statusData.value?.completed_chapters || 0)
const chapters = computed(() => statusData.value?.chapters || [])
const visibleChapters = computed(() => {
  if (!statusFilter.value) return chapters.value
  return chapters.value.filter((row) => row.status === statusFilter.value)
})
const statusFilterOptions = computed(() => [
  { value: "pending", label: t("audio.chapterState.pending") },
  { value: "generating", label: t("audio.chapterState.generating") },
  { value: "completed", label: t("audio.chapterState.completed") },
  { value: "paused", label: t("audio.chapterState.paused") },
  { value: "failed", label: t("audio.chapterState.failed") },
])
const canStart = computed(() => {
  return Boolean(taskId.value) && chapters.value.length > 0 && !isGenerating.value && !busy.value
})
const canStartSelected = computed(() => canStart.value && selectedIndexes.value.length > 0)
const canDeleteSelected = computed(() => {
  return Boolean(taskId.value) && selectedIndexes.value.length > 0 && !isGenerating.value && !busy.value
})
const progressPercent = computed(() => Math.round((statusData.value?.progress || 0) * 100))
const serviceReady = computed(() => apiOnline.value)
const progressStatus = computed(() => {
  if (statusData.value?.status === "failed") return "exception"
  if (statusData.value?.status === "completed") return "success"
  return undefined
})
const statusText = computed(() => mapStatus(statusData.value?.status || "idle"))
const currentStepLabel = computed(() => {
  if (!taskId.value) return t("audio.stepSource")
  if (statusData.value?.status === "parsed") return t("audio.stepGenerate")
  if (statusData.value?.status === "generating") return t("audio.stepRunning")
  if (statusData.value?.status === "paused") return t("audio.stepPaused")
  if (statusData.value?.status === "completed") return t("audio.stepDone")
  return t("audio.stepParse")
})

function handleFileChange(uploadFile) {
  if (!uploadFile.raw) return
  uploadQueue.push({ file: uploadFile.raw, uid: uploadFile.uid })
  processUploadQueue()
}

function handleFileRemove(uploadFile) {
  const index = uploadQueue.findIndex((item) => item.uid === uploadFile.uid)
  if (index >= 0) uploadQueue.splice(index, 1)
}

async function processUploadQueue() {
  if (uploading.value) return

  uploading.value = true
  try {
    while (uploadQueue.length > 0) {
      const item = uploadQueue.shift()
      try {
        await uploadFile(item.file)
      } catch (error) {
        // The request interceptor already shows the error message.
      }
    }
  } finally {
    uploading.value = false
  }
}

function getOutputPathHistory() {
  const saved = getStoredValue(OUTPUT_HISTORY_KEY)
  if (!Array.isArray(saved)) return []
  return saved.filter((item) => typeof item === "string" && item.trim())
}

function rememberOutputPath() {
  const value = outputPath.value.trim()
  if (!value) return

  const history = getOutputPathHistory().filter((item) => item !== value)
  setStoredValue(OUTPUT_HISTORY_KEY, [value, ...history].slice(0, OUTPUT_HISTORY_LIMIT))
}

function fetchOutputPathSuggestions(_queryString, callback) {
  callback(getOutputPathHistory().map((value) => ({ value })))
}

async function uploadFile(file) {
  rememberOutputPath()
  busyAction.value = "upload"
  taskId.value = ""
  statusData.value = null
  localStorage.removeItem(AUDIO_TASK_STORAGE_KEY)
  try {
    const response = await uploadAudioSource({
      file,
      outputPath: outputPath.value.trim(),
      language: locale.value,
    })
    taskId.value = response.task_id
    apiOnline.value = true
    localStorage.setItem(AUDIO_TASK_STORAGE_KEY, response.task_id)
    statusData.value = {
      task_id: response.task_id,
      status: response.status,
      total_chapters: 0,
      completed_chapters: 0,
      progress: 0,
      chapters: [],
    }
    ElMessage.success(response.message || t("audio.uploaded"))
  } finally {
    busyAction.value = ""
  }
}

async function parseSource() {
  busyAction.value = "parse"
  try {
    const response = await parseAudioSource(taskId.value, locale.value)
    // A re-parse replaces the chapter list, so let the table select the new
    // chapters by default.
    selectionInitializedFor.value = ""
    selectedIndexes.value = []
    chapterTableRef.value?.clearSelection()
    statusData.value = {
      ...(statusData.value || {}),
      status: response.status || "parsed",
      total_chapters: 0,
      completed_chapters: 0,
      progress: 0,
      chapters: [],
      error: null,
    }
    await refreshStatus()
    ElMessage.success(t("audio.parsed"))
  } finally {
    busyAction.value = ""
  }
}

async function startChapters(indexes) {
  if (!taskId.value || indexes.length === 0) return

  rememberOutputPath()
  busyAction.value = "start"
  try {
    await generateAudio(taskId.value, {
      voice: voice.value,
      outputPath: outputPath.value.trim(),
      enableLlm: enableLlm.value,
      language: locale.value,
      chapterIndexes: indexes,
    })
    // Poll immediately; a failed status refresh must not stop progress updates.
    startPolling()
    await refreshStatus()
    ElMessage.success(t("audio.generating"))
  } finally {
    busyAction.value = ""
  }
}

function startSelectedChapters() {
  startChapters([...selectedIndexes.value])
}

async function selectAllByDefault() {
  // Check every chapter once, as soon as a task's chapters are first shown
  if (selectionInitializedFor.value === taskId.value) return
  if (chapters.value.length === 0) return

  await nextTick()
  const table = chapterTableRef.value
  if (!table) return

  table.clearSelection()
  chapters.value.forEach((row) => table.toggleRowSelection(row, true))
  selectionInitializedFor.value = taskId.value
}

async function pauseGeneration() {
  if (!taskId.value) return

  busyAction.value = "pause"
  try {
    await pauseAudio(taskId.value)
    ElMessage.info(t("audio.pauseRequested"))
    startPolling()
  } finally {
    busyAction.value = ""
  }
}

async function resumeGeneration() {
  if (!taskId.value) return

  busyAction.value = "resume"
  try {
    await resumeAudio(taskId.value)
    startPolling()
    await refreshStatus()
    ElMessage.success(t("audio.generating"))
  } finally {
    busyAction.value = ""
  }
}

function handleSelectionChange(rows) {
  selectedIndexes.value = rows.map((row) => row.index)
}

function invertSelection() {
  const table = chapterTableRef.value
  if (!table) return

  const selected = new Set(selectedIndexes.value)
  visibleChapters.value.forEach((row) => {
    table.toggleRowSelection(row, !selected.has(row.index))
  })
}

async function deleteSelectedChapters() {
  const indexes = [...selectedIndexes.value]
  if (indexes.length === 0) return

  try {
    await ElMessageBox.confirm(
      t("audio.deleteConfirm", { count: indexes.length }),
      t("audio.deleteTitle"),
      { type: "warning" }
    )
  } catch (error) {
    return
  }

  busyAction.value = "delete"
  // Ignore status responses that were requested before the deletion started.
  stopPolling()
  statusRequestId += 1
  try {
    for (const index of indexes) {
      await deleteChapterAudio(taskId.value, index)
    }
    chapterTableRef.value?.clearSelection()
    selectedIndexes.value = []
    await fetchTaskStatus()
    ElMessage.success(t("audio.deleted"))
  } finally {
    busyAction.value = ""
  }
}

async function loadDefaults() {
  try {
    const status = await getApiStatus({ silent: true })
    apiOnline.value = true
    const defaults = status?.defaults || {}
    if (defaults.voice) voice.value = defaults.voice
    if (typeof defaults.enable_llm === "boolean") enableLlm.value = defaults.enable_llm
  } catch (error) {
    apiOnline.value = false
  }
}

function normalizeTaskStatus(data) {
  // Older backends could keep "completed" after a chapter was deleted. Treat
  // that impossible combination as parsed so the UI cannot show stale results.
  if (
    data?.status === "completed" &&
    Number(data.total_chapters) > 0 &&
    Number(data.completed_chapters) < Number(data.total_chapters)
  ) {
    return { ...data, status: "parsed" }
  }
  return data
}

async function fetchTaskStatus({ silent = false } = {}) {
  const id = taskId.value
  if (!id) return null

  // Only the newest request may update the UI. Without this, a slow polling
  // response can overwrite a newer delete/generate result.
  const requestId = ++statusRequestId
  try {
    const data = normalizeTaskStatus(await getTaskStatus(id, { silent }))
    if (requestId !== statusRequestId || taskId.value !== id) return null

    statusData.value = data
    apiOnline.value = true
    await selectAllByDefault()
    if (TERMINAL_STATUSES.has(data?.status)) stopPolling()
    return data
  } catch (error) {
    if (requestId !== statusRequestId || taskId.value !== id) return null
    stopPolling()
    // Keep the task id for transient network errors; only forget a task
    // that the backend explicitly reports as missing.
    if (error?.response?.status === 404) {
      taskId.value = ""
      statusData.value = null
      localStorage.removeItem(AUDIO_TASK_STORAGE_KEY)
      ElMessage.warning(t("audio.taskExpired"))
    } else {
      apiOnline.value = false
    }
    return null
  }
}

async function loadTask(id) {
  if (!id) return

  stopPolling()
  taskId.value = id
  selectionInitializedFor.value = ""
  localStorage.setItem(AUDIO_TASK_STORAGE_KEY, id)

  const data = await fetchTaskStatus()
  if (data?.status === "generating") {
    startPolling()
  }
}

async function refreshStatus({ silent = false } = {}) {
  await fetchTaskStatus({ silent })
}

async function pollStatus() {
  if (pollInFlight) return
  pollInFlight = true
  try {
    await refreshStatus({ silent: true })
  } finally {
    pollInFlight = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer.value = window.setInterval(pollStatus, 2500)
}

function stopPolling() {
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(() => {
  loadDefaults()
  const savedTaskId = localStorage.getItem(AUDIO_TASK_STORAGE_KEY)
  if (savedTaskId) loadTask(savedTaskId)
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.audio-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--theme-text-color);
  opacity: 0.72;
  font-size: 13px;
  font-weight: 700;
}

.page-heading h1,
.panel h2 {
  margin: 0;
  color: var(--theme-text-color);
}

.page-heading h1 {
  font-size: 28px;
  line-height: 1.25;
  font-weight: 700;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.6fr);
  gap: 18px;
}

.panel {
  background: var(--theme-surface-bg);
  border: 1px solid var(--theme-border-color);
  border-radius: 8px;
  padding: 18px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-header h2 {
  font-size: 17px;
}

.panel-subtitle,
.muted {
  color: var(--theme-muted-text);
  font-size: 13px;
}

.option-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px 160px;
  gap: 14px;
  align-items: end;
  margin-top: 16px;
}

.option-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.voice-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.voice-preview {
  color: var(--theme-primary);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
}

.voice-preview:hover {
  text-decoration: underline;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.chapter-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.chapter-actions .el-button + .el-button {
  margin-left: 0;
}

.status-filter {
  width: 180px;
}

.upload-icon {
  color: var(--theme-primary);
  font-size: 44px;
}

.progress-ring {
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 8px 0 20px;
}

.progress-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--theme-text-color);
}

.progress-copy span,
.mono {
  color: var(--theme-muted-text);
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

.task-meta {
  width: 100%;
}

.chapter-table audio {
  width: 100%;
  height: 34px;
  display: block;
}

@media (max-width: 1100px) {
  .workspace-grid,
  .option-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .panel {
    padding: 14px;
  }

  .action-row .el-button {
    flex: 1;
  }
}
</style>
