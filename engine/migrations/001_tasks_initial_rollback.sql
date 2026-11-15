-- Roll back the v2 task persistence schema.
DROP INDEX IF EXISTS idx_command_log_created_at;
DROP TABLE IF EXISTS command_log;
DROP INDEX IF EXISTS idx_task_events_task_event;
DROP TABLE IF EXISTS task_events;
DROP INDEX IF EXISTS idx_task_chapters_task_status;
DROP TABLE IF EXISTS task_chapters;
DROP INDEX IF EXISTS idx_tasks_updated_at;
DROP INDEX IF EXISTS idx_tasks_status_created_at;
DROP INDEX IF EXISTS uk_tasks_idempotency_key;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS schema_meta;
