-- Apply once through the migration command, not on every request.
CREATE TABLE IF NOT EXISTS semantic_memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0
        CHECK (confidence >= 0 AND confidence <= 1),
    source_thread_id TEXT NOT NULL
        CHECK (length(btrim(source_thread_id)) BETWEEN 1 AND 256),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_semantic_memory_user_key UNIQUE (user_id, memory_key),
    CONSTRAINT ck_semantic_preference CHECK (
        (memory_key = 'preferred_flight_type'
            AND memory_value IN ('non_stop', 'connecting_allowed')) OR
        (memory_key = 'preferred_hotel_class'
            AND memory_value IN ('1_star', '2_star', '3_star', '4_star', '5_star')) OR
        (memory_key = 'preferred_trip_style'
            AND memory_value IN ('budget_friendly', 'balanced', 'luxury'))
    )
);
-- The unique index starts with user_id and also supports user-scoped reads.
