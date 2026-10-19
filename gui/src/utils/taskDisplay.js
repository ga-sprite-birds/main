import { useI18n } from "vue-i18n"

export const AUDIO_TASK_STORAGE_KEY = "audio_task_id"

export function useTaskDisplay() {
  const { t } = useI18n({ useScope: "global" })

  function mapStatus(status) {
    return t(`audio.status.${status || "idle"}`)
  }

  function statusTagType(status) {
    const map = {
      completed: "success",
      failed: "danger",
      generating: "warning",
      parsing: "warning",
      parsed: "primary",
    }
    return map[status] || "info"
  }

  function formatDate(value) {
    if (!value) return "-"
    return new Date(value).toLocaleString()
  }

  return {
    mapStatus,
    statusTagType,
    formatDate,
  }
}
