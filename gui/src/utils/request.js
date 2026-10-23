/**
 * Axios 封装
 */
import axios from "axios";
import { ElMessage } from "element-plus";

const request = axios.create({
    baseURL: `${import.meta.env.VITE_API_BASE_URL || ""}${import.meta.env.VITE_API_PREFIX || ""}`,
    timeout: 30000,
});

// 请求拦截器
request.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// 响应拦截器
request.interceptors.response.use(
    (response) => {
        return response.data;
    },
    (error) => {
        // Background polling passes silent: true to avoid toast spam.
        if (error.config?.silent) {
            return Promise.reject(error);
        }
        if (error.response) {
            const { status, data } = error.response;
            const message = data?.detail || data?.msg || data?.message;
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
