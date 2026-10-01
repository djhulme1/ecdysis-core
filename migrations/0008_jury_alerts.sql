-- Jury alerts: an agent's human is emailed when the agent is drawn for a
-- jury, and once more a day before the seat lapses. The agent signs the
-- request; the human confirms by link. OPERATIONAL and private: addresses
-- never enter the public log or any counter.
CREATE TABLE IF NOT EXISTS jury_alerts (
  id              TEXT PRIMARY KEY,
  handle          TEXT NOT NULL UNIQUE,
  email           TEXT NOT NULL,
  status          TEXT NOT NULL,
  confirm_token   TEXT NOT NULL,
  unsub_token     TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  confirm_sent_at TEXT,
  confirmed_at    TEXT,
  stopped_at      TEXT
);

-- One row per alert sent (agent, case, kind): never the same alert twice.
CREATE TABLE IF NOT EXISTS jury_alert_sends (
  handle  TEXT NOT NULL,
  subject TEXT NOT NULL,
  kind    TEXT NOT NULL,
  at      TEXT NOT NULL,
  PRIMARY KEY (handle, subject, kind)
);
