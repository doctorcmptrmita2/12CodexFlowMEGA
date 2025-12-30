/**
 * Usage Summary Component
 * Displays today's usage, remaining quota, latency, and stage distribution
 */
'use client';

import { useEffect, useState } from 'react';

interface UsageStats {
  todayRequests: number;
  remainingQuota: number;
  dailyLimit: number;
  averageLatency: number;
  stageDistribution: {
    plan: number;
    code: number;
    review: number;
    direct: number;
  };
  resetTime: string; // UTC reset time
}

interface UsageSummaryProps {
  userId: string;
}

export default function UsageSummary({ userId }: UsageSummaryProps) {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUsageStats() {
      try {
        setLoading(true);
        // TODO: Replace with actual API call to router or Supabase
        // For now, stub data
        const response = await fetch(`/api/usage?userId=${userId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch usage stats');
        }
        const data = await response.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    if (userId) {
      fetchUsageStats();
    }
  }, [userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-200">Error: {error}</p>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const quotaPercentage = (stats.remainingQuota / stats.dailyLimit) * 100;

  return (
    <div className="space-y-6">
      {/* Today's Usage */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Today&apos;s Usage
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Requests</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.todayRequests}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Remaining</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.remainingQuota}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Daily Limit</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.dailyLimit}
            </p>
          </div>
        </div>
        
        {/* Quota Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
            <span>Quota Usage</span>
            <span>{quotaPercentage.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                quotaPercentage > 80
                  ? 'bg-red-500'
                  : quotaPercentage > 50
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
              }`}
              style={{ width: `${quotaPercentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Performance
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Average Latency</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.averageLatency}ms
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Quota Resets At</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {stats.resetTime} UTC
            </p>
          </div>
        </div>
      </div>

      {/* Stage Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Stage Distribution
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">Plan</p>
            <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
              {stats.stageDistribution.plan}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">Code</p>
            <p className="text-xl font-bold text-green-600 dark:text-green-400">
              {stats.stageDistribution.code}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">Review</p>
            <p className="text-xl font-bold text-purple-600 dark:text-purple-400">
              {stats.stageDistribution.review}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">Direct</p>
            <p className="text-xl font-bold text-orange-600 dark:text-orange-400">
              {stats.stageDistribution.direct}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

