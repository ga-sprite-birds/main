-- v2 task persistence schema
-- Only the Core engine is allowed to write these tables.

CREATE TABLE IF NOT EXISTS tasks (
  task_id             TEXT PRIMARY KEY,
  type                TEXT NOT NULL,
  status              TEXT NOT NULL,
  phase               TEXT,
  params_json         TEXT NOT NULL DEFAULT '{}',
  result_json         TEXT,
  error               TEXT,
  total_chapters      INTEGER NOT NULL DEFAULT 0,
  completed_chapters  INTEGER NOT NULL DEFAULT 0,
  attempts            INTEGER NOT NULL DEFAULT 0,
  heartbeat_at        TEXT,
  queued_at           TEXT,
  started_at          TEXT,
  finished_at         TEXT,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL,
  idempotency_key     TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_tasks_idempotency_key
  ON tasks (idempotency_key)
  WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_status_created_at
  ON tasks (status, created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at
  ON tasks (updated_at);

CREATE TABLE IF NOT EXISTS task_chapters (
  task_id         TEXT NOT NULL,
  chapter_index   INTEGER NOT NULL,
  title           TEXT NOT NULL,
  status          TEXT NOT NULL,
  content         TEXT,
  audio_path       TEXT,
  error           TEXT,
  attempts        INTEGER NOT NULL DEFAULT 0,
  started_at      TEXT,
  finished_at     TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  PRIMARY KEY (task_id, chapter_index),
  FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_chapters_task_status
  ON task_chapters (task_id, status);

CREATE TABLE IF NOT EXISTS task_events (
  event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       TEXT NOT NULL,
  type          TEXT NOT NULL,
  payload_json  TEXT NOT NULL DEFAULT '{}',
  created_at    TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_event
  ON task_events (task_id, event_id);

CREATE TABLE IF NOT EXISTS command_log (
  command_id    TEXT PRIMARY KEY,
  command       TEXT NOT NULL,
  payload_hash  TEXT NOT NULL,
  status        TEXT NOT NULL,
  result_json   TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_command_log_created_at
  ON command_log (created_at);

CREATE TABLE IF NOT EXISTS schema_meta (
  id                      INTEGER PRIMARY KEY CHECK (id = 1),
  tasks_schema_version    INTEGER NOT NULL,
  updated_at              TEXT NOT NULL
);
