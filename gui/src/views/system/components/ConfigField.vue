<template>
  <el-form-item :label="$t(item.label_i18n)" class="config-field">
    <template #label>
      <span class="field-label">
        <span>{{ $t(item.label_i18n) }}</span>
        <el-tag v-if="item.overridden" size="small" type="warning" effect="plain">
          {{ $t("configPage.overridden") }}
        </el-tag>
      </span>
    </template>

    <div class="field-body">
      <el-switch
        v-if="item.type === 'bool'"
        :model-value="modelValue"
        @update:model-value="update"
      />

      <el-select
        v-else-if="item.type === 'enum'"
        :model-value="modelValue"
        class="field-control"
        popper-class="config-enum-popper"
        @update:model-value="update"
      >
        <el-option
          v-for="option in item.options || []"
          :key="option"
          :label="optionLabel(option)"
          :value="option"
        >
          <div class="option-row">
            <span class="option-label">{{ optionLabel(option) }}</span>
            <span v-if="optionHint(option)" class="option-hint">
              {{ optionHint(option) }}
            </span>
          </div>
        </el-option>
      </el-select>

      <div v-else-if="item.type === 'dynamic-select'" class="voice-row">
        <el-select
          :model-value="modelValue"
          class="field-control voice-select"
          filterable
          allow-create
          default-first-option
          @update:model-value="update"
        >
          <el-option
            v-for="voice in voices"
            :key="voice.ShortName"
            :label="voiceOptionLabel(voice)"
            :value="voice.ShortName"
          />
        </el-select>
        <el-button
          size="small"
          :icon="VideoPlay"
          :loading="previewing"
          :disabled="!modelValue"
          @click="playVoicePreview"
        >
          {{ $t("configPage.preview") }}
        </el-button>
      </div>

      <el-input-number
        v-else-if="item.type === 'int' || item.type === 'float'"
        :model-value="modelValue"
        :min="numberMin"
        :max="numberMax"
        :step="item.type === 'float' ? 0.05 : 1"
        :precision="item.type === 'float' ? 2 : 0"
        controls-position="right"
        @update:model-value="update"
      />

      <el-select
        v-else-if="item.type === 'list[str]'"
        :model-value="Array.isArray(modelValue) ? modelValue : []"
        class="field-control"
        multiple
        filterable
        allow-create
        default-first-option
        @update:model-value="update"
      >
        <el-option
          v-for="value in listOptions"
          :key="value"
          :label="value"
          :value="value"
        />
      </el-select>

      <el-input
        v-else
        :model-value="modelValue"
        :type="isTemplate ? 'textarea' : 'text'"
        :rows="isTemplate ? 2 : undefined"
        :placeholder="placeholder"
        class="field-control"
        @update:model-value="update"
      />

      <!-- 字段说明：先给出整项用途，再解释「当前选中值」的具体含义，
           避免像 off / pause / prosody 这类近似选项选完仍不知道差别 -->
      <p v-if="itemDescription" class="field-desc">{{ itemDescription }}</p>
      <p v-if="selectedOptionHint" class="field-desc option-desc">
        {{ selectedOptionHint }}
      </p>

      <div class="field-meta">
        <span>
          {{ $t("configPage.defaultValue") }}:
          <code>{{ formattedDefault }}</code>
        </span>
        <span v-if="rangeText"> · {{ rangeText }}</span>
      </div>
    </div>
  </el-form-item>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue"
import { useI18n } from "vue-i18n"
import { ElMessage } from "element-plus"
import { VideoPlay } from "@element-plus/icons-vue"

import { getTtsPreviewUrl } from "@/api/systemConfig.js"

const props = defineProps({
  item: { type: Object, required: true },
  modelValue: { required: true },
  voices: { type: Array, default: () => [] },
})
const emit = defineEmits(["update:modelValue"])
const { t, te } = useI18n({ useScope: "global" })

const previewing = ref(false)
let previewAudio = null

function releasePreviewAudio() {
  if (!previewAudio) return
  previewAudio.pause()
  URL.revokeObjectURL(previewAudio.src)
  previewAudio = null
}

// 试听：向 API 取一小段合成音频（带后端缓存），失败时回显后端 i18n 文案。
async function playVoicePreview() {
  const voice = typeof props.modelValue === "string" ? props.modelValue.trim() : ""
  if (!voice || previewing.value) return

  previewing.value = true
  try {
    // cache: "no-store" 必须带上：404 属于浏览器可启发式缓存的状态码，
    // 若之前某次试听接口不可用被缓存，之后同一 URL 会一直回放 404。
    const response = await fetch(getTtsPreviewUrl(voice), { cache: "no-store" })
    const contentType = response.headers.get("content-type") || ""
    if (!response.ok || contentType.includes("application/json")) {
      let message = t("configPage.previewFailed")
      if (response.status === 404) message = t("configPage.previewNotFound")
      try {
        const payload = await response.json()
        // 只认后端下发的 i18n key；"Not found" 这类原始英文保留我们自己的可操作提示
        if (payload?.msg && te(payload.msg)) message = t(payload.msg)
      } catch {
        /* 非 JSON 错误体，保留默认文案 */
      }
      throw new Error(message)
    }
    const blob = await response.blob()
    if (!blob.size) throw new Error(t("configPage.previewFailed"))

    releasePreviewAudio()
    previewAudio = new Audio(URL.createObjectURL(blob))
    try {
      await previewAudio.play()
    } catch (error) {
      // 浏览器自动播放策略拦截（如非真实手势触发）不算试听失败
      if (error?.name !== "NotAllowedError") throw error
    }
  } catch (error) {
    ElMessage.error(error?.message || t("configPage.previewFailed"))
  } finally {
    previewing.value = false
  }
}

onBeforeUnmount(releasePreviewAudio)

const isTemplate = computed(
  () =>
    Array.isArray(props.item.template_fields) ||
    String(props.item.key || "").includes("TEMPLATE"),
)

const placeholder = computed(() =>
  props.item.is_path ? t("configPage.pathPlaceholder") : "",
)

const numberMin = computed(() => {
  if (props.item.ge !== null && props.item.ge !== undefined) return props.item.ge
  if (props.item.gt !== null && props.item.gt !== undefined) return props.item.gt + 1
  return undefined
})

const numberMax = computed(() => {
  if (props.item.le !== null && props.item.le !== undefined) return props.item.le
  if (props.item.lt !== null && props.item.lt !== undefined) return props.item.lt - 1
  return undefined
})

const formattedDefault = computed(() => {
  const value = props.item.default
  if (Array.isArray(value)) return JSON.stringify(value)
  if (typeof value === "boolean") {
    return value ? t("configPage.on") : t("configPage.off")
  }
  return String(value)
})

// 多选列表的候选项：默认值 + 当前值 + 用户已创建的其它值。
// 不能只用当前值，否则删掉某一项后它就从候选项里消失，无法再勾回来。
const listOptions = computed(() => {
  const values = []
  const push = (value) => {
    if (value === null || value === undefined) return
    const text = String(value)
    if (!values.includes(text)) values.push(text)
  }
  if (Array.isArray(props.item.options)) props.item.options.forEach(push)
  if (Array.isArray(props.item.default)) props.item.default.forEach(push)
  if (Array.isArray(props.modelValue)) props.modelValue.forEach(push)
  return values
})

const rangeText = computed(() => {
  const has = (value) => value !== null && value !== undefined
  const parts = []
  if (has(props.item.ge)) parts.push(`≥ ${props.item.ge}`)
  else if (has(props.item.gt)) parts.push(`> ${props.item.gt}`)
  if (has(props.item.le)) parts.push(`≤ ${props.item.le}`)
  else if (has(props.item.lt)) parts.push(`< ${props.item.lt}`)
  return parts.join(" / ")
})

// 后端下发 i18n key（config.desc.<KEY> / config.option.<KEY>.<值>），
// 未翻译时回退为空，枚举值仍显示原始字符串，不会出现空白选项。
function translateKey(key) {
  if (!key) return ""
  return te(key) ? t(key) : ""
}

function optionKey(option, suffix = "") {
  const prefix = props.item.options_i18n
  if (!prefix) return ""
  return `${prefix}.${option}${suffix}`
}

function optionLabel(option) {
  return translateKey(optionKey(option)) || String(option)
}

function optionHint(option) {
  return translateKey(optionKey(option, "_hint"))
}

const itemDescription = computed(() => translateKey(props.item.description_i18n))

const selectedOptionHint = computed(() => {
  if (props.item.type !== "enum") return ""
  if (props.modelValue === null || props.modelValue === undefined) return ""
  return optionHint(String(props.modelValue))
})

function update(value) {
  emit("update:modelValue", value)
}

function voiceOptionLabel(voice) {
  return `${voice.FriendlyName || voice.ShortName} · ${voice.Locale} · ${voice.Gender}`
}
</script>

<style scoped>
.config-field {
  margin-bottom: 22px;
}

.field-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* 控件与默认值提示放入同一纵向容器，避免 el-form-item 的 flex
   布局把提示排到控件同一行（贴在一起） */
.field-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
}

.field-control {
  width: min(100%, 560px);
}

/* 音色下拉 + 试听按钮同一行 */
.voice-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.voice-select {
  flex: 1 1 0;
  width: auto;
  min-width: 0;
}

/* 默认值提示整体使用灰色，值也用同一灰色（不再用深色强调）。
   部分主题的 muted-text 偏深（如经典主题 #555550），再降一点不透明度，
   让它与背景混合成更明确的浅灰，深色主题下也不会过亮。 */
.field-meta {
  color: var(--theme-muted-text);
  opacity: 0.78;
  font-size: 12px;
  line-height: 1.5;
}

/* 字段说明比「默认值」更需要阅读，灰得浅一点并放宽行高 */
.field-desc {
  width: min(100%, 560px);
  margin: 0;
  color: var(--theme-muted-text);
  font-size: 12px;
  line-height: 1.65;
}

.field-desc.option-desc {
  color: var(--theme-text-color);
  opacity: 0.86;
}

/* 下拉选项：左译文 + 右侧灰色说明 */
.option-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.option-label {
  flex: 0 0 auto;
}

.option-hint {
  flex: 1 1 auto;
  overflow: hidden;
  color: var(--theme-muted-text);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-meta code {
  color: inherit;
  font-size: inherit;
  background: none;
  padding: 0;
  word-break: break-all;
}
</style>

<!-- 下拉面板被 teleport 到 body，scoped 样式够不到，这里写全局样式：
     面板按内容加宽，长说明换行而不是被省略号截断。 -->
<style>
.config-enum-popper {
  width: auto !important;
  min-width: 460px;
  max-width: min(760px, 92vw);
}

.config-enum-popper .el-select-dropdown__item {
  height: auto;
  min-height: 34px;
  padding: 7px 12px;
  line-height: 1.55;
  white-space: normal;
}

.config-enum-popper .option-row .option-hint {
  white-space: normal;
}
</style>
