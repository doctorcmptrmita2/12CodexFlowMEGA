/**
 * Logs Page - Request Logs with Filters
 * Displays filtered request logs with sorting and pagination
 */
'use client';

import { useState } from 'react';
import Filters, { FilterState } from '@/components/Filters';
import LogsTable from '@/components/LogsTable';

// TODO: Get userId from authentication (Supabase Auth or session)
// For now, using placeholder - will be replaced with actual auth
const PLACEHOLDER_USER_ID = 'user-id-placeholder';

export default function LogsPage() {
  const [filters, setFilters] = useState<FilterState>({
    stage: 'all',
    model: 'all',
    status: 'all',
    timeRange: 'today',
  });

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Request Logs
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            View and filter your AI orchestration request logs
          </p>
        </div>

        {/* Filters */}
        <Filters onFilterChange={handleFilterChange} />

        {/* Logs Table */}
        <LogsTable userId={PLACEHOLDER_USER_ID} filters={filters} />

        {/* Info Banner */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Note:</strong> Logs are fetched from Supabase with Row Level Security (RLS)
            enabled. You can only view your own request logs. Data includes tokens, cost, latency,
            and status for each request.
          </p>
        </div>
      </div>
    </div>
  );
}

