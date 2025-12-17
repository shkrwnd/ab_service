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

### Primary metric + significance (results)

- **Primary metric**: results can treat one event type (ex: `purchase`) as the main “conversion” metric.
  - Implemented via `primary_event_type` (query param) and computed per variant:
    - `primary_event_count`, `primary_unique_users`, `primary_conversion_rate`
- **Significance**: baseline vs treatment comparison includes a two-proportion z-test:
  - `z_score`, `p_value`, `significant`, and a 95% CI for the conversion-rate difference.

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
- `GET /experiments/{experiment_id}/results`: Analytics/results with optional filters: `start_date`, `end_date`, `event_type`, `variant_id`.

## Next Improvement

- Pre-aggregated metrics (daily/hourly tables + background job) so results stay fast at high event volume.


