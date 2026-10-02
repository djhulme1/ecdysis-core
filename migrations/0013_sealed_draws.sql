-- jury/0.5: how each case's panel is drawn. The log key's signature over
-- the receipt (made after the submission arrived), the seed derived from
-- it, and the first round it governs, as JSON. Set once, never replaced.
-- Cases seated before jury/0.5 keep NULL (their panels were drawn with the
-- receipt itself as the seed) until their next redraw seals them.
ALTER TABLE quarantine ADD COLUMN draw_json TEXT;
