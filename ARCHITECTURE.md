# Architecture Overview

## Architecture / Stack

- **FastAPI**: speed, async support, request/response validation (Pydantic), and auto docs.
- **SQLite**: zero-setup simplicity; easy to swap to PostgreSQL later via connection string.
- **SQLAlchemy ORM**: clean DB access and easier future migrations.

## Database Model

- **experiments**: metadata
- **variants**: traffic split
- **user_assignments**: which user got which variant
- **events**: tracking + JSON properties stored as text

Important bits:
- Unique constraint on `(experiment_id, user_id)` to keep assignments idempotent.
- Indexes on common filters (`user_id`, `timestamp`, `event_type`, `experiment_id`).
- `assigned_at` ensures results only count events after assignment.

## Assignment Logic

- Hash `user_id + experiment_id` → number 0–99 → map into variant traffic buckets → store in DB + cache.
- Pros: deterministic, idempotent, fair distribution, simple.
- Trade-off: hard to change traffic split mid-experiment without reassignment.

## Results Endpoint

- One flexible endpoint with query params (date range, event type, variant).
- Core rule: only count events where `event.timestamp ≥ assigned_at`.
- Returns experiment info + summary totals + per-variant metrics + lift/comparison.

### Query Parameters

- `start_date`, `end_date`: Filter events by time range (ISO format).
- `event_type`: Filter to specific event type (e.g., `purchase`).
- `variant_id`: Filter to specific variant.
- `primary_event_type`: Treat one event type as the "conversion" metric (e.g., `purchase`).
- `group_by`: Time-series aggregation (`day` or `hour`).

### Response Structure

**Base metrics (always present):**
- `experiment`: Experiment metadata + variants.
- `summary`: Total assigned users, total events, date range.
- `variants`: Per-variant metrics:
  - `assigned_count`, `event_count`, `events_by_type`, `conversion_rate`, `unique_users_with_events`
  - If `primary_event_type` is set: `primary_event_count`, `primary_unique_users`, `primary_conversion_rate`, `primary_events_per_assigned_user`

**Primary metric (optional):**
- When `primary_event_type` is provided, conversion metrics focus on that event type only.
- Example: `primary_event_type=purchase` means "conversion" = users who made a purchase (not just any event).

**Statistical significance:**
- `comparison`: Baseline vs first treatment (backward compatibility).
- `comparisons`: **All variants vs baseline** (multi-variant comparisons):
  - Each entry includes: `lift_percentage`, `z_score`, `p_value`, `significant`, `conversion_rate_diff_ci_95`
  - Uses two-proportion z-test (pooled SE for z-score, unpooled for CI).

**Time-series aggregation (optional):**
- When `group_by=day` or `group_by=hour`, returns `timeseries` array:
  - Each row: `bucket` (ISO timestamp), `variants` (per-variant: assigned, events, conversions, conversion_rate)
  - Useful for monitoring trends over time, detecting early wins/losses, spotting anomalies.

**SRM (Sample Ratio Mismatch) detection:**
- `srm`: Detects if observed assignment split deviates from expected traffic split.
  - Compares expected % (from variant `traffic_percentage`) vs observed % (from actual assignments).
  - Uses chi-square goodness-of-fit test with Wilson–Hilferty approximation for p-value.
  - `flagged: true` when p < 0.01 (indicates potential instrumentation bug, targeting issue, or bot traffic).
  - Fields: `expected_split_percent`, `observed_split_percent`, `chi_square`, `df`, `p_value`, `flagged`.

## Caching

In-memory TTL cache:
- `assignment:{experiment_id}:{user_id}`
- `experiment:{experiment_id}`

Fast and simple for single instance; Redis later for multi-instance.

## Authentication

- Simple Bearer token list from env vars.
- Production: add expiry/rotation, stronger auth (JWT/OAuth2), rate limiting.

## Endpoints

- `GET /health`: Health check (returns service status).
- `POST /experiments`: Create a new experiment (with variants + traffic split).
- `GET /experiments/{experiment_id}`: Fetch an experiment by ID (includes variants).
- `GET /experiments/{experiment_id}/assignment/{user_id}`: Get (or create) deterministic variant assignment for a user.
- `POST /events`: Record tracking events (single or batch).
- `GET /experiments/{experiment_id}/results`: Analytics/results with optional filters:
  - **Filters**: `start_date`, `end_date`, `event_type`, `variant_id`
  - **Analysis modes**: `primary_event_type` (conversion metric), `group_by` (time-series: `day`/`hour`)
  - Returns: experiment metadata, per-variant metrics, multi-variant comparisons (lift + significance), optional time-series, SRM health check.

## Results Processing Flow

1. **Query events + assignments**: Join `events` with `user_assignments` (only events after `assigned_at`).
2. **Apply filters**: Date range, event type, variant (if provided).
3. **Aggregate per variant**: Count assigned users, events, conversions (primary metric if specified).
4. **Compute comparisons**: For each variant vs baseline → lift, z-test, p-value, CI.
5. **Time-series (if requested)**: Bucket by day/hour, compute per-bucket metrics per variant.
6. **SRM check**: Compare expected vs observed assignment split → chi-square → flag if suspicious.
7. **Return**: Structured response with all computed metrics.

## Next Improvement

- Pre-aggregated metrics (daily/hourly tables + background job) so results stay fast at high event volume.


