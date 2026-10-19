<template>
  <el-aside
    :width="collapsed ? collapsedWidth + 'px' : width + 'px'"
    class="layout-aside"
    :class="{ 'layout-aside-classic': isClassicTheme }"
    :style="asideStyle"
  >
    <el-menu
      :default-active="route.path"
      :collapse="collapsed"
      router
      class="sidebar-menu"
      :class="{ 'sidebar-menu-classic': isClassicTheme }"
      :style="menuStyle"
    >
      <el-menu-item index="/policy/dashboard">
        <el-icon><Headset /></el-icon>
        <template #title>{{ $t("route.dashboard") }}</template>
      </el-menu-item>

      <el-menu-item index="/policy/tasks">
        <el-icon><List /></el-icon>
        <template #title>{{ $t("route.tasks") }}</template>
      </el-menu-item>

      <el-menu-item index="/policy/theme">
        <el-icon><Setting /></el-icon>
        <template #title>{{ $t("theme.settings") }}</template>
      </el-menu-item>

    </el-menu>
  </el-aside>
</template>

<script setup>
import { computed } from "vue"
import { useRoute } from "vue-router"
import { useThemeStore } from "@/store/modules/theme.js"
import { Headset, List, Setting } from "@element-plus/icons-vue"

defineProps({
  collapsed: { type: Boolean, default: false },
  width: { type: Number, default: 200 },
  collapsedWidth: { type: Number, default: 64 },
})

const route = useRoute()
const themeStore = useThemeStore()
const isClassicTheme = computed(() => themeStore.themeAppearance === "photoshop-cs3")

const asideStyle = computed(() => ({
  backgroundColor: "var(--theme-aside-bg)",
  transition: "width 0.3s ease, background-color 0.3s ease",
  borderRight: isClassicTheme.value ? "1px solid var(--theme-border-dark)" : "none",
  boxShadow: isClassicTheme.value ? "inset -1px 0 0 var(--theme-border-light)" : "none",
}))

const menuStyle = computed(() => ({
  borderRight: "none",
  height: "100%",
  "--el-menu-active-color": isClassicTheme.value ? "var(--theme-text-color)" : "var(--theme-primary)",
}))
</script>

<style scoped>
.layout-aside {
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--theme-aside-text);
  --el-menu-hover-bg-color: var(--theme-hover-bg);
  --el-menu-hover-text-color: var(--theme-primary);
}

.dark .sidebar-menu {
  --el-menu-text-color: var(--theme-aside-text);
  --el-menu-hover-bg-color: var(--theme-hover-bg);
  --el-menu-hover-text-color: var(--theme-primary);
}

.sidebar-menu .el-menu-item.is-active {
  position: relative;
}

:root:not(.dark) .sidebar-menu .el-menu-item.is-active {
  background: var(--theme-active-bg);
}

.dark .sidebar-menu .el-menu-item.is-active {
  background: var(--theme-active-bg);
}

.sidebar-menu .el-menu-item.is-active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 2px 2px 0;
  background: var(--theme-primary);
  transition: background-color 0.3s ease;
}

.sidebar-menu-classic {
  --el-menu-text-color: var(--theme-aside-text);
  --el-menu-hover-bg-color: var(--theme-hover-bg);
  --el-menu-hover-text-color: var(--theme-text-color);
}

.sidebar-menu-classic .el-menu-item:hover,
.sidebar-menu-classic .el-sub-menu__title:hover {
  background: linear-gradient(to bottom, var(--theme-surface-gradient-start), var(--theme-hover-bg));
  color: var(--theme-text-color);
  box-shadow: inset 1px 1px 0 var(--theme-border-light), inset -1px -1px 0 rgba(255, 255, 255, 0.1);
}

.sidebar-menu-classic .el-menu-item.is-active {
  background: linear-gradient(to bottom, var(--el-color-primary-light-3), var(--el-color-primary));
  color: var(--theme-header-text);
  box-shadow: inset 1px 1px 0 rgba(255, 255, 255, 0.28), inset -1px -1px 0 rgba(0, 0, 0, 0.18);
}

:root[data-theme-appearance="photoshop-cs3"][data-theme-mode="light"] .sidebar-menu-classic .el-menu-item.is-active {
  background: linear-gradient(to bottom, #777872, #555650);
  color: #ffffff;
  box-shadow: inset 1px 1px 0 rgba(255, 255, 255, 0.25), inset -1px -1px 0 rgba(0, 0, 0, 0.26);
}

.dark .sidebar-menu-classic .el-menu-item:hover,
.dark .sidebar-menu-classic .el-sub-menu__title:hover {
  color: var(--theme-text-color);
}

.dark .sidebar-menu-classic .el-menu-item.is-active {
  color: var(--theme-header-text);
}

.sidebar-menu-classic .el-menu-item:hover .el-icon,
.sidebar-menu-classic .el-sub-menu__title:hover .el-icon {
  color: var(--theme-text-color);
}

.sidebar-menu-classic .el-menu-item.is-active .el-icon {
  color: var(--theme-header-text);
}

:root[data-theme-appearance="photoshop-cs3"][data-theme-mode="light"] .sidebar-menu-classic .el-menu-item.is-active .el-icon {
  color: #ffffff;
}

.dark .sidebar-menu-classic .el-menu-item:hover .el-icon,
.dark .sidebar-menu-classic .el-sub-menu__title:hover .el-icon {
  color: var(--theme-text-color);
}

.dark .sidebar-menu-classic .el-menu-item.is-active .el-icon {
  color: var(--theme-header-text);
}

.sidebar-menu-classic .el-menu-item.is-active::before {
  background: var(--theme-workspace-bg);
}

:root[data-theme-appearance="photoshop-cs3"][data-theme-mode="light"] .sidebar-menu-classic .el-menu-item.is-active::before {
  width: 4px;
  height: 26px;
  background: var(--theme-workspace-bg);
}

.dark .sidebar-menu-classic .el-menu-item.is-active::before {
  background: var(--theme-control-bg-raised);
}
</style>
