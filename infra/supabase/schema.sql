-- CF-X Supabase Schema
-- Run this in Supabase SQL Editor or via Supabase CLI
-- Usage: supabase db push (if using Supabase CLI)

-- ============================================
-- 1. Users Table (extends Supabase Auth)
-- ============================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    plan TEXT DEFAULT 'starter' CHECK (plan IN ('starter', 'pro', 'agency')),
    daily_limit INTEGER,
    streaming_concurrency_cap INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
DROP POLICY IF EXISTS "Users can view own data" ON public.users;
CREATE POLICY "Users can view own data" ON public.users
    FOR SELECT USING (auth.uid() = id);

-- ============================================
-- 2. API Keys Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON public.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON public.api_keys(status);

-- Enable RLS
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own keys
DROP POLICY IF EXISTS "Users can view own keys" ON public.api_keys;
CREATE POLICY "Users can view own keys" ON public.api_keys
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- 3. Usage Counters Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.usage_counters (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    day DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, day)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_usage_counters_user_day ON public.usage_counters(user_id, day);

-- Enable RLS
ALTER TABLE public.usage_counters ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own counters
DROP POLICY IF EXISTS "Users can view own counters" ON public.usage_counters;
CREATE POLICY "Users can view own counters" ON public.usage_counters
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- 4. Request Logs Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,
    request_id TEXT NOT NULL,
    session_id TEXT,
    stage TEXT NOT NULL CHECK (stage IN ('plan', 'code', 'review', 'direct')),
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'error')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_request_logs_user ON public.request_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_request_logs_created ON public.request_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_request_logs_stage ON public.request_logs(stage);
CREATE INDEX IF NOT EXISTS idx_request_logs_status ON public.request_logs(status);
CREATE INDEX IF NOT EXISTS idx_request_logs_user_created ON public.request_logs(user_id, created_at DESC);

-- Enable RLS
ALTER TABLE public.request_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own logs
DROP POLICY IF EXISTS "Users can view own logs" ON public.request_logs;
CREATE POLICY "Users can view own logs" ON public.request_logs
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- 5. RPC Function: Atomic Increment Usage Counter
-- ============================================

CREATE OR REPLACE FUNCTION increment_usage_counter(
    p_user_id UUID,
    p_day DATE,
    p_limit INTEGER DEFAULT 1000
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
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

