/**
 * Dashboard Page - Read-Only Overview
 * Displays usage summary, quota, and performance metrics
 */
import { Suspense } from 'react';
import UsageSummary from '@/components/UsageSummary';

// TODO: Get userId from authentication (Supabase Auth or session)
// For now, using placeholder - will be replaced with actual auth
const PLACEHOLDER_USER_ID = 'user-id-placeholder';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            CF-X Dashboard
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Monitor your AI orchestration usage and performance
          </p>
        </div>

        {/* Usage Summary */}
        <Suspense
          fallback={
            <div className="flex items-center justify-center p-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          }
        >
          <UsageSummary userId={PLACEHOLDER_USER_ID} />
        </Suspense>

        {/* Info Banner */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Note:</strong> This dashboard is read-only. All data is fetched from Supabase
            with Row Level Security (RLS) enabled. You can only view your own usage data.
          </p>
        </div>
      </div>
    </div>
  );
}

