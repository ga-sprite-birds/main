/**
 * Axios 封装
 */
import axios from "axios";
import { ElMessage } from "element-plus";

export const API_TOKEN_STORAGE_KEY = "ga_api_token";
export const API_TOKEN_COOKIE = "ga_api_token";

export function getApiToken() {
    try {
        return localStorage.getItem(API_TOKEN_STORAGE_KEY) || "";
    } catch {
        return "";
    }
}

function applyTokenCookie(token) {
    if (typeof document === "undefined") return;
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    if (token) {
        document.cookie = `${API_TOKEN_COOKIE}=${encodeURIComponent(token)}; Path=/; SameSite=Strict${secure}`;
    } else {
        document.cookie = `${API_TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Strict${secure}`;
    }
}

export function setApiToken(token) {
    const value = String(token || "").trim();
    try {
        if (value) {
            localStorage.setItem(API_TOKEN_STORAGE_KEY, value);
        } else {
            localStorage.removeItem(API_TOKEN_STORAGE_KEY);
        }
    } catch {
        // localStorage may be unavailable; the in-memory cookie still works.
    }
    applyTokenCookie(value);
}

// Keep direct <audio>/<a> requests authenticated (they cannot set headers).
applyTokenCookie(getApiToken());

const request = axios.create({
    baseURL: `${import.meta.env.VITE_API_BASE_URL || ""}${import.meta.env.VITE_API_PREFIX || ""}`,
    timeout: 30000,
});

// 请求拦截器
request.interceptors.request.use(
    (config) => {
        const token = getApiToken();
        if (token && !config.headers?.Authorization) {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// 响应拦截器
request.interceptors.response.use(
    (response) => {
        const payload = response.data;
        if (payload && typeof payload === "object" && "code" in payload) {
            if (payload.code !== 0) {
                const error = new Error(payload.msg || "请求失败");
                error.code = payload.code;
                error.data = payload.data;
                error.response = { status: 200, data: payload };
                if (!response.config?.silent) {
                    ElMessage.error(payload.msg || "请求失败");
                }
                return Promise.reject(error);
            }
            return payload.data;
        }
        return payload;
    },
    (error) => {
        // Background polling passes silent: true to avoid toast spam.
        if (error.config?.silent) {
            return Promise.reject(error);
        }
        if (error.response) {
            const { status, data } = error.response;
            const message = data?.msg || data?.detail || data?.message;
            switch (status) {
                case 401:
                    ElMessage.error(message || "请求未授权");
                    break;
                case 403:
                    ElMessage.error(message || "权限不足");
                    break;
                case 404:
                    ElMessage.error(message || "请求的资源不存在");
                    break;
                case 503:
                    ElMessage.error(message || "Core 引擎未运行");
                    break;
                case 500:
                    ElMessage.error(message || "服务器内部错误");
                    break;
                default:
                    ElMessage.error(message || "网络错误");
            }
        } else {
            ElMessage.error("网络连接失败");
        }
        return Promise.reject(error);
    },
);

export default request;
