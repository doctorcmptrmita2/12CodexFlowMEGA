/**
 * Usage API Route
 * Fetches usage statistics from Supabase with RLS
 */
import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const userId = searchParams.get('userId');
    
    if (!userId) {
      return NextResponse.json(
        { error: 'userId is required' },
        { status: 400 }
      );
    }
    
    const supabase = createServerClient();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString().split('T')[0];
    
    // Get today's usage counter
    const { data: counterData, error: counterError } = await supabase
      .from('usage_counters')
      .select('request_count')
      .eq('user_id', userId)
      .eq('day', todayStr)
      .single();
    
    if (counterError && counterError.code !== 'PGRST116') {
      // PGRST116 = no rows returned (expected if no requests today)
      console.error('Supabase error:', counterError);
    }
    
    const todayRequests = counterData?.request_count || 0;
    const dailyLimit = 1000; // TODO: Get from user plan
    const remainingQuota = Math.max(0, dailyLimit - todayRequests);
    
    // Get today's request logs for statistics
    const { data: logsData, error: logsError } = await supabase
      .from('request_logs')
      .select('latency_ms, stage, status')
      .eq('user_id', userId)
      .gte('created_at', today.toISOString());
    
    if (logsError) {
      console.error('Supabase error:', logsError);
    }
    
    // Calculate statistics
    const logs = logsData || [];
    const successfulLogs = logs.filter(log => log.status === 'success');
    const averageLatency = successfulLogs.length > 0
      ? Math.round(
          successfulLogs.reduce((sum, log) => sum + (log.latency_ms || 0), 0) /
          successfulLogs.length
        )
      : 0;
    
    // Stage distribution
    const stageDistribution = {
      plan: logs.filter(log => log.stage === 'plan').length,
      code: logs.filter(log => log.stage === 'code').length,
      review: logs.filter(log => log.stage === 'review').length,
      direct: logs.filter(log => log.stage === 'direct').length,
    };
    
    // Calculate reset time (next day 00:00 UTC)
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setUTCHours(0, 0, 0, 0);
    const resetTime = tomorrow.toISOString().split('T')[1].split('.')[0] + ' UTC';
    
    return NextResponse.json({
      todayRequests,
      remainingQuota,
      dailyLimit,
      averageLatency,
      stageDistribution,
      resetTime
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

