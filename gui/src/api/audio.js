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
      language: options.language,
    },
  })
}

export function getTaskStatus(taskId) {
  return request({
    url: `/task/${taskId}/status`,
    method: "get",
  })
}

export function listTasks() {
  return request({
    url: "/tasks",
    method: "get",
  })
}

export function getChapterAudioUrl(taskId, chapterIndex, version) {
  const baseUrl = `${import.meta.env.VITE_API_BASE_URL || ""}${import.meta.env.VITE_API_PREFIX || ""}`
  const suffix = version ? `?v=${encodeURIComponent(version)}` : ""
  return `${baseUrl}/task/${taskId}/chapter/${chapterIndex}${suffix}`
}
