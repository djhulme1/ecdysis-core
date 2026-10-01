-- Preprints: a paper under review may be readable at once, by the author's
-- signed choice and only when screening found nothing. It is not part of the
-- record: not in the log, not citable, not buildable, and withdrawn if the
-- jury does not accept it. preprint_at is when it became readable.
ALTER TABLE quarantine ADD COLUMN preprint_at TEXT;
CREATE INDEX IF NOT EXISTS quarantine_by_preprint ON quarantine(preprint_at);
