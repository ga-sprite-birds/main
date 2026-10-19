<template>
  <div class="page-container page-container--wide task-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">{{ appTitle }}</p>
        <h1>{{ $t("audio.taskList") }}</h1>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadTasks">
        {{ $t("audio.refresh") }}
      </el-button>
    </section>

    <section class="panel">
      <el-empty v-if="!loading && tasks.length === 0" :description="$t('audio.emptyTasks')" />
      <el-table
        v-else
        v-loading="loading"
        :data="tasks"
        class="task-table"
        row-key="task_id"
        highlight-current-row
        @row-click="openTask"
      >
        <el-table-column prop="filename" :label="$t('audio.taskFile')" min-width="220" show-overflow-tooltip />
        <el-table-column :label="$t('audio.taskStatus')" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain">
              {{ mapStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('audio.taskChapters')" width="120">
          <template #default="{ row }">
            {{ row.completed_chapters }}/{{ row.total_chapters }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('audio.taskCreated')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('audio.taskAction')" width="100" align="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="openTask(row)">
              {{ $t("audio.taskLoad") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { Refresh } from "@element-plus/icons-vue"
import { listTasks } from "@/api/audio.js"
import { AUDIO_TASK_STORAGE_KEY, useTaskDisplay } from "@/utils/taskDisplay.js"

const router = useRouter()
const appTitle = import.meta.env.VITE_APP_TITLE || "GA Sprite Birds"
const tasks = ref([])
const loading = ref(false)
let refreshTimer = null

const { mapStatus, statusTagType, formatDate } = useTaskDisplay()

async function loadTasks(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    tasks.value = await listTasks()
  } catch (error) {
    // Keep the current list when the task endpoint is temporarily unavailable.
  } finally {
    if (showLoading) loading.value = false
  }
}

function openTask(row) {
  localStorage.setItem(AUDIO_TASK_STORAGE_KEY, row.task_id)
  router.push({
    path: "/policy/dashboard",
    query: { task: row.task_id },
  })
}

onMounted(() => {
  loadTasks()
  refreshTimer = window.setInterval(() => loadTasks(false), 5000)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.task-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--theme-text-color);
  opacity: 0.72;
  font-size: 13px;
  font-weight: 700;
}

.page-heading h1 {
  margin: 0;
  color: var(--theme-text-color);
  font-size: 28px;
  line-height: 1.25;
  font-weight: 700;
}

.panel {
  background: var(--theme-surface-bg);
  border: 1px solid var(--theme-border-color);
  border-radius: 8px;
  padding: 18px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.task-table {
  width: 100%;
}

.task-table :deep(.el-table__row) {
  cursor: pointer;
}

@media (max-width: 720px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .panel {
    padding: 14px;
  }
}
</style>
