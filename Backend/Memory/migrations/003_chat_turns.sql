-- A memory event prevents duplicate extraction. A chat receipt additionally
-- prevents an HTTP retry from being mistaken for a new clarification answer.
CREATE TABLE chat_turn_receipts (
    user_id UUID NOT NULL,
    message_id UUID NOT NULL,
    thread_id TEXT NOT NULL,
    memory_context JSONB NOT NULL,
    memory_selected_ids JSONB NOT NULL,
    response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (user_id, message_id),
    FOREIGN KEY (user_id, message_id) REFERENCES memory_events(user_id, message_id),
    FOREIGN KEY (thread_id, user_id) REFERENCES memory_threads(thread_id, user_id)
);

-- Preserve unfinished work across API process restarts. A different message
-- must wait until the caller retries the original message ID successfully.
ALTER TABLE memory_threads ADD COLUMN active_message_id UUID;
ALTER TABLE memory_threads ADD CONSTRAINT memory_thread_active_turn
    FOREIGN KEY (user_id, active_message_id)
    REFERENCES chat_turn_receipts(user_id, message_id);
