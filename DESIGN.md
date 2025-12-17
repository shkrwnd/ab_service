# Design Document

## Architecture Decisions

### Technology Stack

**FastAPI**: Chosen for its modern async support, automatic API documentation, and excellent performance. The type hints and Pydantic integration make it easy to validate requests/responses.

**SQLite**: Started with SQLite for simplicity and zero-configuration. The schema is designed to be easily portable to PostgreSQL when needed - just change the connection string.

**SQLAlchemy ORM**: Provides a clean abstraction over the database and makes migrations easier. The models are straightforward and don't over-engineer relationships.

### Database Schema

The schema follows a standard experimentation platform pattern:

1. **experiments**: Core experiment metadata
2. **variants**: Variants within an experiment with traffic percentages
3. **user_assignments**: Tracks which variant each user is assigned to (with unique constraint for idempotency)
4. **events**: Flexible event storage with JSON properties

**Key Design Choices**:
- `user_assignments` has a unique constraint on `(experiment_id, user_id)` - this is critical for idempotency
- Events store properties as JSON strings (SQLite doesn't have native JSON, but this works fine)
- Indexes on commonly queried fields: user_id, timestamp, event_type, experiment_id
- `assigned_at` timestamp is crucial - results only count events after this time

### Assignment Algorithm

The assignment logic uses a deterministic hash-based approach:

1. Hash `user_id + experiment_id` to get a value 0-99
2. Map that value to a variant based on traffic percentage buckets
3. Store assignment in database with timestamp
4. Cache assignment for performance

**Why this approach?**
- Deterministic: Same user + experiment always gets same variant
- Idempotent: Database unique constraint prevents duplicates
- Fair distribution: Hash function provides good distribution
- Simple: No complex state management needed

**Trade-offs**:
- Can't easily change traffic allocation mid-experiment (would require reassignment)
- Hash collisions are possible but rare with good hash function
- Traffic percentages must sum to 100% (enforced in validation)

### Results Endpoint Design

The results endpoint is designed to be flexible and support multiple use cases:

**Use Cases Supported**:
1. **Real-time monitoring**: Quick overview of experiment performance
2. **Deep analysis**: Filter by date, event type, variant
3. **Executive summaries**: High-level metrics and lift calculations

**Key Implementation Details**:
- Only counts events where `event.timestamp >= user_assignment.assigned_at`
- This ensures we don't count events that happened before a user was assigned
- Uses SQL joins for efficiency rather than loading everything into memory
- Calculates conversion rates, event counts, and lift metrics

**Query Parameters Philosophy**:
Instead of creating separate endpoints for different views, I chose query parameters. This keeps the API surface small while allowing flexibility. Could add more parameters later (like `group_by=day` for time-series) without breaking changes.

**Response Structure**:
The response includes:
- Experiment metadata
- Summary statistics
- Per-variant metrics
- Comparison/lift calculations

This structure supports both programmatic consumption and human-readable reports.

### Caching Strategy

Implemented a simple in-memory cache using `cachetools` with TTL:

- **Assignment cache**: Key = `assignment:{experiment_id}:{user_id}`
- **Experiment cache**: Key = `experiment:{experiment_id}`

**Why in-memory?**
- Simple to implement and understand
- Fast for single-instance deployments
- Easy to swap to Redis later if needed (just change cache implementation)

**Trade-offs**:
- Doesn't work across multiple instances (would need Redis)
- Cache invalidation is time-based only (could add manual invalidation)
- Memory usage grows with cache size (but we have max size limits)

### Authentication

Simple Bearer token authentication with token list from environment variable.

**Why this approach?**
- Meets the requirement (Bearer token auth)
- Simple to implement and understand
- Easy to extend later (add token expiration, refresh tokens, etc.)

**Production considerations**:
- Would want to add token expiration
- Consider OAuth2 or JWT for production
- Rate limiting per token
- Token rotation mechanisms

## Trade-offs & Decisions

### SQLite vs PostgreSQL

**Chose SQLite** because:
- Zero configuration
- Perfect for development and small deployments
- Easy to swap to PostgreSQL later (just change connection string)

**Downsides**:
- Limited concurrent writes
- No advanced features (JSON columns, full-text search, etc.)
- File-based (can't easily scale horizontally)

### In-Memory Cache vs Redis

**Chose in-memory** because:
- Simpler for initial implementation
- No external dependencies
- Fast for single-instance deployments

**Would use Redis** for:
- Multi-instance deployments
- Shared cache across services
- More advanced caching patterns

### Flexible Event Properties vs Strict Schema

**Chose flexible JSON properties** because:
- Supports various event types without schema changes
- Easy to add new properties
- Matches real-world experimentation needs

**Trade-offs**:
- No validation of property structure
- Harder to query on specific properties
- Could lead to inconsistent data

### Assignment Algorithm: Hash-based vs Random

**Chose hash-based** because:
- Deterministic (same user always gets same variant)
- No state needed to track assignments
- Fair distribution

**Alternative approaches**:
- Random assignment with database lookup (slower, requires DB hit every time)
- Pre-assignment (faster but requires knowing user list upfront)

## Production Scaling Considerations

### Database

1. **Migrate to PostgreSQL**: Better for concurrent writes, advanced features
2. **Read replicas**: For read-heavy workloads (results queries)
3. **Connection pooling**: Use SQLAlchemy connection pooler
4. **Database indexes**: Already have indexes, but monitor query performance

### Caching

1. **Redis cluster**: For distributed caching across instances
2. **Cache warming**: Pre-populate cache for hot experiments
3. **Cache invalidation**: More sophisticated invalidation strategies

### Assignment

1. **Pre-assignment**: For high-traffic experiments, pre-assign users in batch
2. **Assignment service**: Separate microservice for assignments if needed
3. **Assignment storage**: Consider Redis for very high-traffic scenarios

### Events

1. **Event streaming**: Use Kafka or similar for high-volume event ingestion
2. **Async processing**: Don't block API on event writes
3. **Event batching**: Already support batch creation, but could optimize further
4. **Event archival**: Move old events to cold storage

### Results/Analytics

1. **Pre-aggregated tables**: Materialized views or scheduled jobs to pre-compute metrics
2. **Time-series database**: For detailed time-based analysis
3. **Caching results**: Cache common queries (e.g., last 7 days)
4. **Background jobs**: Calculate results asynchronously for large experiments

### API

1. **Rate limiting**: Per-token or per-IP rate limits
2. **Request queuing**: For high-traffic endpoints
3. **API versioning**: Add versioning when making breaking changes
4. **Monitoring**: Add metrics, logging, alerting

## Next Priority Improvement

**Pre-aggregated metrics tables**: For large-scale experiments with millions of events, the results endpoint can be slow. I would prioritize implementing:

1. **Materialized views** or **scheduled aggregation jobs** that pre-compute:
   - Event counts per variant per day
   - Conversion rates
   - Unique user counts

2. **Incremental updates**: Update aggregates as new events come in

3. **Query optimization**: Results endpoint queries pre-aggregated data instead of raw events

This would reduce query time from seconds (for large experiments) to milliseconds, making the API much more responsive for real-time monitoring dashboards.

**Implementation approach**:
- Add `experiment_metrics_daily` table
- Background job (Celery or similar) that runs every hour/day
- Results endpoint checks if pre-aggregated data exists, falls back to real-time if not
- Could use database triggers or event-driven updates for near-real-time aggregation

## What I'd Do Differently

1. **Add experiment status transitions**: Currently status is just a string, but would add state machine validation (draft -> active -> paused -> completed)

2. **Better error handling**: More specific error messages, error codes

3. **API versioning**: Should have started with `/v1/` prefix for future compatibility

4. **More comprehensive tests**: Add integration tests, load tests

5. **Logging**: Add structured logging throughout (currently just print statements)

6. **Documentation**: Auto-generated OpenAPI docs are good, but could add more examples

7. **Assignment metadata**: Store more info about assignment (e.g., which traffic bucket, hash value) for debugging

8. **Event validation**: Add schema validation for event properties based on event type

