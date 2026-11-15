import request from "@/utils/request.js"

export function getSystemConfig() {
    return request({
        url: "/system-config",
        method: "get",
    })
}

export function updateSystemConfig(values) {
    return request({
        url: "/system-config",
        method: "put",
        data: { values },
    })
}

export function resetSystemConfig(payload) {
    return request({
        url: "/system-config/reset",
        method: "post",
        data: payload,
    })
}

export function getTtsVoices(params = {}) {
    return request({
        url: "/tts/voices",
        method: "get",
        params,
        silent: params.silent,
        timeout: 60000,
    })
}

/** 音色试听音频地址（二进制，直接给 <audio>/fetch 用，不走信封解包）。 */
export function getTtsPreviewUrl(voice, text) {
    const baseUrl = `${import.meta.env.VITE_API_BASE_URL || ""}${import.meta.env.VITE_API_PREFIX || ""}`
    const params = new URLSearchParams({ voice })
    if (text) params.set("text", text)
    return `${baseUrl}/tts/preview?${params.toString()}`
}
