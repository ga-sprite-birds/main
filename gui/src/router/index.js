import { createRouter, createWebHistory } from "vue-router";
import routes from "@/router/routes.js";
import i18n from "@/i18n/index.js";

const router = createRouter({
    history: createWebHistory(),
    routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
    const title = to.meta.title;
    document.title = title ? i18n.global.t(title) : import.meta.env.VITE_APP_TITLE || "GA Sprite Birds";

    next();
});

export default router;
