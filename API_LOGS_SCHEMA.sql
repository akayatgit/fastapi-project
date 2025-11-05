-- Supabase Table Schema for API Logs
-- This table stores detailed logs of all API calls for data analysis

CREATE TABLE api_logs (
  id bigserial PRIMARY KEY,
  timestamp timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  endpoint text NOT NULL,
  interests text,
  mapped_categories jsonb,
  mapping_method text,  -- 'llm', 'keyword_fallback', or 'error'
  total_matching_events integer,
  selected_event_id bigint,
  selected_event_name text,
  selected_event_category text,
  success boolean NOT NULL,
  error_message text,
  response_time_ms numeric,
  client_ip text,
  user_agent text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Add indexes for faster analytics queries
CREATE INDEX idx_api_logs_timestamp ON api_logs(timestamp DESC);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_success ON api_logs(success);
CREATE INDEX idx_api_logs_interests ON api_logs(interests);
CREATE INDEX idx_api_logs_selected_event_id ON api_logs(selected_event_id);
CREATE INDEX idx_api_logs_mapping_method ON api_logs(mapping_method);  -- Track LLM vs fallback usage

-- Add comment
COMMENT ON TABLE api_logs IS 'Stores detailed logs of API calls to /api/event/by-interests for data analysis and debugging';

-- If table already exists, add the new column
-- ALTER TABLE api_logs ADD COLUMN IF NOT EXISTS mapping_method text;

