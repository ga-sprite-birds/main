import PolicyLayout from "@/components/layout/PolicyLayout.vue"
import AudioWorkbench from "@/views/policy/audio/AudioWorkbench.vue"
import TaskList from "@/views/policy/tasks/index.vue"
import ThemePage from "@/views/policy/theme/index.vue"

const policyRoutes = [
    {
        path: "/policy",
        component: PolicyLayout,
        redirect: "/policy/dashboard",
        children: [
            {
                path: "dashboard",
                name: "PolicyDashboard",
                component: AudioWorkbench,
                meta: { title: "route.dashboard" },
            },
            {
                path: "tasks",
                name: "PolicyTasks",
                component: TaskList,
                meta: { title: "route.tasks" },
            },
            {
                path: "theme",
                name: "PolicyTheme",
                component: ThemePage,
                meta: { title: "theme.settings" },
            },
        ],
    },
];

export default policyRoutes;
