'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { Message, Pagination } from '@/types';
import { format } from 'date-fns';
import { ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import toast from 'react-hot-toast';

export default function MessagesPage() {
  const { selectedBusiness } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({
    direction: '',
    status: '',
  });

  useEffect(() => {
    if (selectedBusiness) {
      loadMessages();
    }
  }, [selectedBusiness, currentPage, filters]);

  const loadMessages = async () => {
    if (!selectedBusiness) return;

    try {
      setLoading(true);
      const data = await apiClient.getMessages(selectedBusiness.id, {
        page: currentPage,
        limit: 20,
        ...(filters.direction && { direction: filters.direction }),
        ...(filters.status && { status: filters.status }),
      });
      setMessages(data.messages);
      setPagination(data.pagination);
    } catch (error) {
      toast.error('Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Messages</h1>
            <p className="text-gray-600 mt-1">View and manage all conversations</p>
          </div>
          <Button variant="secondary">
            <Filter size={16} className="mr-2" />
            Filters
          </Button>
        </div>

        {/* Filter Pills */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilters({ ...filters, direction: '' })}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              filters.direction === ''
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilters({ ...filters, direction: 'inbound' })}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              filters.direction === 'inbound'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Inbound
          </button>
          <button
            onClick={() => setFilters({ ...filters, direction: 'outbound' })}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              filters.direction === 'outbound'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Outbound
          </button>
        </div>

        {/* Messages List */}
        <Card>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No messages found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold ${
                        message.direction === 'inbound' ? 'bg-blue-600' : 'bg-green-600'
                      }`}
                    >
                      {message.sender_name?.[0] || 'U'}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {message.sender_name || message.sender_phone}
                        </p>
                        <p className="text-xs text-gray-500">
                          {format(new Date(message.created_at), 'MMM dd, yyyy HH:mm')}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            message.direction === 'inbound'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-green-100 text-green-800'
                          }`}
                        >
                          {message.direction}
                        </span>
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
                    </div>
                    <p className="text-sm text-gray-700 mt-2">{message.content}</p>
                    {message.language_detected && (
                      <p className="text-xs text-gray-500 mt-1">
                        Language: {message.language_detected}
                        {message.processing_time_ms && ` • ${message.processing_time_ms}ms`}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {pagination && pagination.pages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-6 border-t">
              <p className="text-sm text-gray-600">
                Page {pagination.page} of {pagination.pages} ({pagination.total} total)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(currentPage - 1)}
                >
                  <ChevronLeft size={16} />
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage === pagination.pages}
                  onClick={() => setCurrentPage(currentPage + 1)}
                >
                  <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
