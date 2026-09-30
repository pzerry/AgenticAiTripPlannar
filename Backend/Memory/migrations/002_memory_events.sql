-- Durable event inbox: capture commits before any model call.
CREATE TABLE memory_users (
    user_id UUID PRIMARY KEY,
    last_sequence BIGINT NOT NULL DEFAULT 0 CHECK (last_sequence >= 0)
);
CREATE TABLE memory_threads (
    thread_id TEXT PRIMARY KEY CHECK (length(thread_id) BETWEEN 1 AND 256),
    user_id UUID NOT NULL REFERENCES memory_users(user_id),
    UNIQUE (thread_id, user_id)
);
CREATE TABLE memory_events (
    user_id UUID NOT NULL REFERENCES memory_users(user_id),
    message_id UUID NOT NULL,
    thread_id TEXT NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence > 0),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    payload_hash TEXT NOT NULL,
    source_text TEXT CHECK (length(source_text) BETWEEN 1 AND 32000),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'complete', 'failed', 'expired')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    lease_token UUID,
    lease_until TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    error_code TEXT,
    PRIMARY KEY (user_id, message_id),
    UNIQUE (user_id, sequence),
    FOREIGN KEY (thread_id, user_id) REFERENCES memory_threads(thread_id, user_id)
);
CREATE INDEX memory_events_queue ON memory_events (available_at, occurred_at)
    WHERE status IN ('pending', 'processing');

-- Values live only in semantic_memories. A deletion retains this small ordering
-- record, without the old value or evidence text, to fence stale extraction.
CREATE TABLE memory_versions (
    user_id UUID NOT NULL REFERENCES memory_users(user_id),
    memory_key TEXT NOT NULL CHECK (memory_key IN
        ('preferred_flight_type', 'preferred_hotel_class', 'preferred_trip_style')),
    source_sequence BIGINT NOT NULL,
    source_message_id UUID NOT NULL,
    revision BIGINT NOT NULL DEFAULT 1 CHECK (revision > 0),
    deleted BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (user_id, memory_key),
    FOREIGN KEY (user_id, source_message_id) REFERENCES memory_events(user_id, message_id)
);
