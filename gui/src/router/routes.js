import AppLayout from "@/components/layout/AppLayout.vue"
import AudioWorkbench from "@/views/audio/AudioWorkbench.vue"
import ThemePage from "@/views/theme/index.vue"

const routes = [
    {
        path: "/",
        component: AppLayout,
        redirect: "/dashboard",
        children: [
            {
                path: "dashboard",
                name: "Dashboard",
                component: AudioWorkbench,
                meta: { title: "route.dashboard" },
            },
            {
                path: "theme",
                name: "Theme",
                component: ThemePage,
                meta: { title: "theme.settings" },
            },
            {
                path: "system/config",
                name: "SystemConfig",
                component: () => import("@/views/system/config.vue"),
                meta: { title: "route.systemConfig" },
            },
        ],
    },
    {
        path: "/:pathMatch(.*)*",
        redirect: "/dashboard",
    },
]

export default routes
