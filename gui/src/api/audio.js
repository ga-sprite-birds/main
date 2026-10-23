import request from "@/utils/request.js"

export function uploadAudioSource({ file, path, outputPath, language }) {
  const formData = new FormData()
  if (file) {
    formData.append("file", file)
  }

  return request({
    url: "/upload",
    method: "post",
    params: {
      path: path || undefined,
      output_path: outputPath || undefined,
      language: language || undefined,
    },
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data",
    },
    // Large books can take far longer than the default 30s to upload.
    timeout: 0,
  })
}

export function parseAudioSource(taskId, language) {
  return request({
    url: "/parse",
    method: "post",
    data: {
      task_id: taskId,
      language,
    },
  })
}

export function generateAudio(taskId, options = {}) {
  return request({
    url: "/generate",
    method: "post",
    data: {
      task_id: taskId,
      voice: options.voice || undefined,
      output_path: options.outputPath || undefined,
      enable_llm: options.enableLlm,
      rate: options.rate,
      prosody_mode: options.prosodyMode || undefined,
      language: options.language,
      chapter_indexes: options.chapterIndexes || undefined,
    },
  })
}

export function pauseAudio(taskId) {
  return request({
    url: `/task/${taskId}/pause`,
    method: "post",
  })
}

export function resumeAudio(taskId) {
  return request({
    url: `/task/${taskId}/resume`,
    method: "post",
  })
}

export function deleteChapterAudio(taskId, chapterIndex) {
  return request({
    url: `/task/${taskId}/chapter/${chapterIndex}`,
    method: "delete",
  })
}

export function clearAudioTask(taskId) {
  return request({
    url: `/task/${taskId}`,
    method: "delete",
    // The view handles 404 and other clear failures with a friendly message.
    silent: true,
  })
}

export function getTaskStatus(taskId, options = {}) {
  return request({
    url: `/task/${taskId}/status`,
    method: "get",
    // Bypass any HTTP cache so a deleted chapter cannot reappear.
    params: { _: Date.now() },
    // A chapter merge can block briefly; do not abandon polling on that.
    timeout: 120000,
    silent: options.silent,
  })
}

export function getApiStatus(options = {}) {
  return request({
    url: "/api/status",
    method: "get",
    silent: options.silent,
  })
}

export function getChapterAudioUrl(taskId, chapterIndex, version) {
  const baseUrl = `${import.meta.env.VITE_API_BASE_URL || ""}${import.meta.env.VITE_API_PREFIX || ""}`
  const suffix = version ? `?v=${encodeURIComponent(version)}` : ""
  return `${baseUrl}/task/${taskId}/chapter/${chapterIndex}${suffix}`
}
