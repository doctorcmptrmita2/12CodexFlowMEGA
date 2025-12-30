/**
 * Logs API Route
 * Fetches request logs from Supabase with RLS
 */
import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const userId = searchParams.get('userId');
    const page = parseInt(searchParams.get('page') || '1');
    const pageSize = parseInt(searchParams.get('pageSize') || '20');
    const sortBy = searchParams.get('sortBy') || 'created_at';
    const sortOrder = searchParams.get('sortOrder') || 'desc';
    
    // Filters
    const stage = searchParams.get('stage');
    const model = searchParams.get('model');
    const status = searchParams.get('status');
    const timeRange = searchParams.get('timeRange');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    
    if (!userId) {
      return NextResponse.json(
        { error: 'userId is required' },
        { status: 400 }
      );
    }
    
    const supabase = createServerClient();
    
    // Build query
    let query = supabase
      .from('request_logs')
      .select('*', { count: 'exact' })
      .eq('user_id', userId)
      .order(sortBy, { ascending: sortOrder === 'asc' });
    
    // Apply filters
    if (stage && stage !== 'all') {
      query = query.eq('stage', stage);
    }
    
    if (model && model !== 'all') {
      query = query.eq('model', model);
    }
    
    if (status && status !== 'all') {
      query = query.eq('status', status);
    }
    
    // Time range filter
    if (timeRange && timeRange !== 'all') {
      const now = new Date();
      let start: Date | undefined;
      
      switch (timeRange) {
        case 'today':
          start = new Date(now.setHours(0, 0, 0, 0));
          break;
        case 'yesterday':
          start = new Date(now.setDate(now.getDate() - 1));
          start.setHours(0, 0, 0, 0);
          break;
        case 'last7days':
          start = new Date(now.setDate(now.getDate() - 7));
          break;
        case 'last30days':
          start = new Date(now.setDate(now.getDate() - 30));
          break;
        case 'custom':
          if (startDate && endDate) {
            start = new Date(startDate);
            const end = new Date(endDate);
            query = query.gte('created_at', start.toISOString());
            query = query.lte('created_at', end.toISOString());
          }
          break;
        default:
          // Unknown timeRange, skip filter
          break;
      }
      
      if (timeRange !== 'custom' && start) {
        query = query.gte('created_at', start.toISOString());
      }
    }
    
    // Pagination
    const from = (page - 1) * pageSize;
    const to = from + pageSize - 1;
    query = query.range(from, to);
    
    const { data, error, count } = await query;
    
    if (error) {
      console.error('Supabase error:', error);
      return NextResponse.json(
        { error: 'Failed to fetch logs' },
        { status: 500 }
      );
    }
    
    const totalPages = Math.ceil((count || 0) / pageSize);
    
    return NextResponse.json({
      logs: data || [],
      totalPages,
      page,
      pageSize,
      total: count || 0
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

