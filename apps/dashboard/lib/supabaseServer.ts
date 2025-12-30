/**
 * Supabase Server-Side Client
 * Uses ANON_KEY only (NO service role key in dashboard)
 * RLS (Row Level Security) ensures users can only read their own data
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY'
  );
}

// Type assertion: we've checked above that these are defined
const url: string = supabaseUrl;
const key: string = supabaseAnonKey;

/**
 * Create Supabase client for server-side operations
 * This client uses ANON_KEY and relies on RLS for security
 */
export function createServerClient() {
  return createClient(url, key, {
    auth: {
      persistSession: false,
    },
  });
}

/**
 * Get Supabase client with user session
 * For authenticated requests (if using Supabase Auth)
 */
export async function getAuthenticatedClient(userId: string) {
  const client = createServerClient();
  // Note: In production, you'd set the session here
  // For now, RLS will handle authorization based on user_id
  return client;
}

