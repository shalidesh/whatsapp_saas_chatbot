'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card } from '@/components/ui/Card';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { DashboardStatistics, Message } from '@/types';
import { MessageSquare, CheckCircle, Clock, FileText, TrendingUp } from 'lucide-react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const { selectedBusiness } = useAuthStore();
  const [stats, setStats] = useState<DashboardStatistics | null>(null);
  const [recentMessages, setRecentMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedBusiness) {
      loadDashboardData();
    }
  }, [selectedBusiness]);

  const loadDashboardData = async () => {
    if (!selectedBusiness) return;

    try {
      setLoading(true);
      const data = await apiClient.getOverview(selectedBusiness.id);
      setStats(data.statistics);
      setRecentMessages(data.recent_messages);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome back! Here's what's happening.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="border-l-4 border-l-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Messages</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {stats?.total_messages || 0}
                </p>
              </div>
              <MessageSquare className="text-blue-500" size={40} />
            </div>
          </Card>

          <Card className="border-l-4 border-l-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Response Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {stats?.response_rate.toFixed(1) || 0}%
                </p>
              </div>
              <CheckCircle className="text-green-500" size={40} />
            </div>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Response Time</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {((stats?.avg_response_time_ms || 0) / 1000).toFixed(1)}s
                </p>
              </div>
              <Clock className="text-purple-500" size={40} />
            </div>
          </Card>

          <Card className="border-l-4 border-l-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Documents</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {stats?.processed_documents || 0}/{stats?.total_documents || 0}
                </p>
              </div>
              <FileText className="text-orange-500" size={40} />
            </div>
          </Card>
        </div>

        {/* Recent Messages */}
        <Card title="Recent Messages" subtitle="Latest conversations with customers">
          <div className="space-y-4">
            {recentMessages.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No messages yet</p>
            ) : (
              recentMessages.map((message) => (
                <div
                  key={message.id}
                  className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {message.sender_name?.[0] || 'U'}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium text-gray-900">
                        {message.sender_name || message.sender_phone}
                      </p>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          message.status === 'responded'
                            ? 'bg-green-100 text-green-800'
                            : message.status === 'processing'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {message.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 truncate">{message.content}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {format(new Date(message.created_at), 'MMM dd, yyyy HH:mm')}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <div className="text-center py-4">
              <MessageSquare className="mx-auto text-blue-600 mb-3" size={32} />
              <h3 className="font-semibold text-gray-900">View Messages</h3>
              <p className="text-sm text-gray-600 mt-1">Browse all conversations</p>
            </div>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <div className="text-center py-4">
              <FileText className="mx-auto text-orange-600 mb-3" size={32} />
              <h3 className="font-semibold text-gray-900">Upload Documents</h3>
              <p className="text-sm text-gray-600 mt-1">Add knowledge base content</p>
            </div>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <div className="text-center py-4">
              <TrendingUp className="mx-auto text-green-600 mb-3" size={32} />
              <h3 className="font-semibold text-gray-900">View Analytics</h3>
              <p className="text-sm text-gray-600 mt-1">Check performance metrics</p>
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
