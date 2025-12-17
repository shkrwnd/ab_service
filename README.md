# A/B Testing API Service

A FastAPI-based service for managing A/B tests, user assignments, and tracking experiment performance.

## Features

- Create experiments with multiple variants and configurable traffic allocation
- Idempotent user assignment (same user always gets same variant)
- Flexible event tracking with JSON properties
- **Comprehensive results/analytics endpoint** with:
  - Statistical significance testing (z-test, p-values, confidence intervals)
  - Primary metric analysis (focus on specific event types like "purchase")
  - Multi-variant comparisons (all variants vs baseline)
  - Time-series aggregation (daily/hourly trends)
  - SRM (Sample Ratio Mismatch) detection for traffic split health
- Bearer token authentication
- Caching for performance
- Docker deployment ready

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)

### Local Development

1. **Clone and setup**:
```bash
cd ab_service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
# Copy .env.example to .env and set your API token
export API_TOKEN="your-secret-token-here"
export DATABASE_URL="sqlite:///./ab_testing.db"
```

3. **Run the server**:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or run in background
docker-compose up -d
```

## API Endpoints

All endpoints require Bearer token authentication. Include the token in the Authorization header:
```
Authorization: Bearer your-secret-token-here
```

For end-to-end request examples (curl), see `examples/usage.sh`.

### 1. Create Experiment

```bash
POST /experiments
```

**Request Body**:
```json
{
  "name": "Button Color Test",
  "description": "Testing red vs blue button",
  "variants": [
    {"name": "control", "traffic_percentage": 50.0},
    {"name": "variant_b", "traffic_percentage": 50.0}
  ]
}
```

**Response**: Experiment details with variants

### 2. Get User Assignment

```bash
GET /experiments/{experiment_id}/assignment/{user_id}
```

Returns the variant assigned to a user. This endpoint is **idempotent** - calling it multiple times with the same user_id and experiment_id will always return the same assignment.

**Response**:
```json
{
  "experiment_id": 1,
  "user_id": "user_123",
  "variant_id": 2,
  "variant_name": "variant_b",
  "assigned_at": "2024-01-15T10:30:00"
}
```

### 3. Record Event

```bash
POST /events
```

**Request Body** (single event):
```json
{
  "user_id": "user_123",
  "type": "purchase",
  "timestamp": "2024-01-15T10:35:00",
  "properties": {
    "amount": 29.99,
    "product": "widget"
  },
  "experiment_id": 1
}
```

**Request Body** (batch events):
```json
[
  {
    "user_id": "user_123",
    "type": "click",
    "timestamp": "2024-01-15T10:35:00"
  },
  {
    "user_id": "user_456",
    "type": "purchase",
    "timestamp": "2024-01-15T10:36:00"
  }
]
```

### 4. Get Experiment Results

```bash
GET /experiments/{experiment_id}/results?start_date=2024-01-01&end_date=2024-01-31&event_type=purchase&primary_event_type=purchase&group_by=day
```

**Query Parameters**:
- `start_date` (optional): Filter events from this date (ISO format)
- `end_date` (optional): Filter events until this date (ISO format)
- `event_type` (optional): Filter by specific event type
- `variant_id` (optional): Filter by specific variant
- `primary_event_type` (optional): Treat this event type as the "conversion" metric (e.g., `purchase`)
- `group_by` (optional): Time-series aggregation - `day` or `hour` for trend analysis

**Response**:
```json
{
  "experiment": {
    "id": 1,
    "name": "Button Color Test",
    "status": "active",
    "variants": [...]
  },
  "summary": {
    "total_assigned": 1000,
    "total_events": 5000,
    "date_range": {
      "start": "2024-01-01T00:00:00",
      "end": "2024-01-31T23:59:59"
    }
  },
  "variants": [
    {
      "variant_id": 1,
      "variant_name": "control",
      "assigned_count": 500,
      "event_count": 2500,
      "events_by_type": {"click": 2000, "purchase": 500},
      "conversion_rate": 0.5,
      "unique_users_with_events": 450,
      "primary_event_type": "purchase",
      "primary_event_count": 500,
      "primary_unique_users": 400,
      "primary_conversion_rate": 0.8,
      "primary_events_per_assigned_user": 1.0
    }
  ],
  "comparison": {
    "baseline": "control",
    "treatment": "variant_b",
    "lift_percentage": 20.0,
    "z_score": 2.45,
    "p_value": 0.014,
    "significant": true,
    "conversion_rate_diff_ci_95": {"diff_low": 0.02, "diff_high": 0.18}
  },
  "comparisons": [
    {
      "baseline": "control",
      "baseline_variant_id": 1,
      "treatment": "variant_b",
      "treatment_variant_id": 2,
      "lift_percentage": 20.0,
      "p_value": 0.014,
      "significant": true,
      "metric": "purchase"
    }
  ],
  "timeseries": [
    {
      "bucket": "2024-01-15T00:00:00",
      "group_by": "day",
      "metric": "purchase",
      "variants": [
        {
          "variant_id": 1,
          "variant_name": "control",
          "assigned": 50,
          "events": 200,
          "conversions": 40,
          "conversion_rate": 0.8
        }
      ]
    }
  ],
  "srm": {
    "total_assigned": 1000,
    "expected_split_percent": {"1": 50.0, "2": 50.0},
    "observed_split_percent": {"1": 49.8, "2": 50.2},
    "chi_square": 0.08,
    "df": 1,
    "p_value": 0.78,
    "flagged": false
  }
}
```

**Key Features**:
- **Statistical Significance**: `comparison` and `comparisons` include z-test results (p-value, z-score, 95% CI)
- **Primary Metric**: When `primary_event_type` is set, conversion metrics focus on that event type
- **Multi-Variant Comparisons**: `comparisons` array shows all variants vs baseline (not just first two)
- **Time-Series**: `timeseries` array (when `group_by` is used) shows daily/hourly trends per variant
- **SRM Detection**: `srm` object flags if assignment split deviates from expected traffic allocation (indicates potential bugs)

**Important**: Results only count events that occur **after** a user's assignment timestamp.

## Running Tests

```bash
pytest tests/
```

## Project Structure

```
ab_service/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── database.py          # DB setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   └── utils/               # Utilities (caching, assignment)
├── tests/                   # Unit tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Configuration

Environment variables (see `.env.example`):
- `API_TOKEN`: Comma-separated list of valid Bearer tokens
- `DATABASE_URL`: Database connection string
- `CACHE_TTL`: Cache time-to-live in seconds
- `CACHE_MAX_SIZE`: Maximum cache size

## Example Usage

See `examples/usage.sh` for complete examples demonstrating all endpoints.

## License

MIT

