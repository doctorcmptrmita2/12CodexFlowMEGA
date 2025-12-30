-- Supabase RPC Function: increment_usage_counter
-- Atomic increment with conflict handling
-- Usage: SELECT increment_usage_counter(user_id, day, limit)
-- Returns: JSON with request_count, allowed, limit

CREATE OR REPLACE FUNCTION increment_usage_counter(
    p_user_id UUID,
    p_day DATE,
    p_limit INTEGER DEFAULT 1000
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_request_count INTEGER;
    v_allowed BOOLEAN;
BEGIN
    -- Insert or update with atomic increment
    INSERT INTO usage_counters (user_id, day, request_count, updated_at)
    VALUES (p_user_id, p_day, 1, NOW())
    ON CONFLICT (user_id, day)
    DO UPDATE SET
        request_count = usage_counters.request_count + 1,
        updated_at = NOW()
    RETURNING request_count INTO v_request_count;
    
    -- Check if limit exceeded
    v_allowed := v_request_count <= p_limit;
    
    -- Return result as JSON
    RETURN json_build_object(
        'request_count', v_request_count,
        'allowed', v_allowed,
        'limit', p_limit
    );
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION increment_usage_counter(UUID, DATE, INTEGER) TO service_role;

