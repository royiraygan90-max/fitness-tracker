# Design: Live Workout Weight Input & Previous Workout Display

**Date:** 2026-06-08  
**Status:** Approved

---

## Overview

Two features added to Live Workout Mode:

1. **Previous Workout Data Display** — show a compact "LAST: 3 × 8 @ 10 kg" summary line per exercise, drawn from the most recent completed workout of the same type (A or B).
2. **Per-Set Weight Input** — add a weight field (ק"ג) next to each set's reps input, stored alongside reps in the database.

---

## Schema & Data Model

### Migration

Add one nullable TEXT column to `workout_exercises`:

```sql
ALTER TABLE workout_exercises ADD COLUMN weight_kg TEXT;
```

- Stores per-set weights as comma-separated values, e.g. `"10,10,10"` or `"7.5,7.5,8"` — same format as the existing `reps` column.
- NULL on all existing rows. Backward-compatible: history and all existing queries treat NULL as "no weight".
- `_create_tables` updated to include `weight_kg TEXT` in the `CREATE TABLE IF NOT EXISTS` for new installs.
- A `_migrate_db` helper runs at startup via `PRAGMA table_info(workout_exercises)` and issues the `ALTER TABLE` only if the column is absent (safe to call repeatedly).

---

## Backend

### New endpoint: `GET /api/workouts/previous/<workout_type>`

- Accepts only `workout_a` or `workout_b`; returns 400 for any other value.
- Queries for the single most-recent `workouts` row of that type (by `date DESC, created_at DESC`).
- Joins `workout_exercises` and returns all exercises for that workout.
- Parses `reps` and `weight_kg` CSV strings into arrays.

**Success response (workout found):**
```json
{
  "workout_type": "workout_a",
  "date": "2026-06-03",
  "exercises": [
    {
      "name": "Pull-up",
      "sets": 3,
      "reps": ["8", "8", "7"],
      "weights": ["10", "10", "10"]
    }
  ]
}
```

**No previous workout:**
```json
{ "previous": null }
```

### Updated: `POST /log/live`

Accepts an optional `weights` field per exercise in the JSON body:

```json
{
  "workout_type": "workout_a",
  "date": "2026-06-08",
  "exercises": [
    { "name": "Pull-up", "sets": 3, "reps": "8,8,7", "weights": "10,10,10" }
  ]
}
```

- `weights` is optional. Missing or empty → stores NULL in `weight_kg` (backward-compatible).
- Sanitised to max 200 chars.

### Updated: `GET /history`

`GROUP_CONCAT` gains a fourth pipe-delimited segment:

```sql
GROUP_CONCAT(
  we.exercise_name || '|' || COALESCE(we.sets,'') || '|' ||
  COALESCE(we.reps,'') || '|' || COALESCE(we.weight_kg,''),
  ';;'
)
```

Parse loop in the route splits out the fourth field. Template renders:

- With weight present: `10 reps × 10 kg` (first value from the CSV)
- Without weight (NULL/empty): `10 reps` — unchanged from today

---

## Frontend — Live Workout Mode (`live_workout.html`)

### Previous workout fetch

On page load, immediately `fetch('/api/workouts/previous/<WORKOUT_TYPE>')`. Store result in a `previousData` object keyed by exercise name. If `previous: null`, `previousData` is empty.

### "LAST" summary line

Above the sets container, for the current exercise, inject a read-only `<div class="lw-last-summary">` when previous data exists:

```
LAST: 3 × 8 @ 10 kg
```

- Format: `<sets_count> × <first_reps_value> @ <first_weight_value> kg`
- If previous data has no weight: `LAST: 3 × 8` (no `@` part)
- If no previous data for this exercise: element is hidden / absent
- Styled as small muted grey text, below the exercise target line

### Per-set weight input

Each `.lw-set-row` gains a weight input to the right of the reps input:

```
[✓] Set 1   [__reps__]  [__weight__] ק"ג
```

Input attributes:
- `type="number"`, `step="0.5"`, `min="0"`, `placeholder="ק\"ג"`
- Default value: empty (not 0)
- `aria-label="Weight for set <N>"`

### State

`state[i].sets` entries become `{ checked, reps, weight }`. Weight is tracked via `input` event, same as reps.

Previous workout weight is **not** pre-populated into the input — user fills fresh each session.

### `finishWorkout()`

Collects weights per-exercise as a comma-separated string:

```js
weights: checked.map(s => s.weight || '').join(',')
```

Included in the POST payload alongside `reps`.

---

## Tests (additions to `tests/test_app.py`)

| Test | Assertion |
|------|-----------|
| `test_previous_workout_none` | Fresh DB → `GET /api/workouts/previous/workout_a` returns `{"previous": null}` |
| `test_previous_workout_returns_last` | Log two workout_a entries → endpoint returns the more recent one with correct exercise name/reps/weights |
| `test_log_live_with_weights` | POST `/log/live` with `weights` field → 200, data retrievable via previous-workout endpoint |
| `test_previous_workout_invalid_type` | `GET /api/workouts/previous/poci` → 400 |

---

## Backward Compatibility

- All existing rows have `weight_kg = NULL`. History renders identically.
- `POST /log/live` without `weights` field works unchanged.
- `GET /api/workouts/previous/<type>` is new; existing code paths are unaffected.
- Migration (`ALTER TABLE`) is idempotent and runs at startup before any request is served.
