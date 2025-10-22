'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { Bot, Send, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface AgentConfig {
  business_name: string;
  ai_persona: string;
  supported_languages: string[];
  default_language: string;
  vector_db_type: string;
  status: string;
}

interface TestResponse {
  response: string;
  language_detected: string;
  confidence: number;
  processing_time_ms: number;
}

export default function AIAgentPage() {
  const { selectedBusiness } = useAuthStore();
  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [testMessage, setTestMessage] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResponse | null>(null);
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    if (selectedBusiness) {
      loadAgentStatus();
    }
  }, [selectedBusiness]);

  const loadAgentStatus = async () => {
    if (!selectedBusiness) return;

    try {
      setLoading(true);
      const data = await apiClient.getAgentStatus(selectedBusiness.id);
      setAgentConfig(data.agent_config);
    } catch (error) {
      toast.error('Failed to load agent status');
    } finally {
      setLoading(false);
    }
  };

  const handleTestMessage = async () => {
    if (!selectedBusiness || !testMessage.trim()) return;

    try {
      setTesting(true);
      const data = await apiClient.testAIMessage(selectedBusiness.id, testMessage);
      setTestResult(data.ai_response);
      toast.success('Message processed successfully');
    } catch (error) {
      toast.error('Failed to process message');
    } finally {
      setTesting(false);
    }
  };

  const handleReloadKnowledge = async () => {
    if (!selectedBusiness) return;

    try {
      setReloading(true);
      await apiClient.reloadKnowledge(selectedBusiness.id);
      toast.success('Knowledge base reload initiated');
    } catch (error) {
      toast.error('Failed to reload knowledge base');
    } finally {
      setReloading(false);
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
      <div className="space-y-6 max-w-6xl">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Agent</h1>
          <p className="text-gray-600 mt-1">Test and monitor your AI agent</p>
        </div>

        {/* Agent Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="border-l-4 border-l-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Agent Status</p>
                <p className="text-2xl font-bold text-gray-900 mt-2 capitalize">
                  {agentConfig?.status || 'Unknown'}
                </p>
              </div>
              {agentConfig?.status === 'active' ? (
                <CheckCircle className="text-green-500" size={40} />
              ) : (
                <XCircle className="text-red-500" size={40} />
              )}
            </div>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <div>
              <p className="text-sm font-medium text-gray-600">Supported Languages</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {agentConfig?.supported_languages.map((lang) => (
                  <span
                    key={lang}
                    className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                  >
                    {lang.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
          </Card>

          <Card className="border-l-4 border-l-purple-500">
            <div>
              <p className="text-sm font-medium text-gray-600">Vector Database</p>
              <p className="text-2xl font-bold text-gray-900 mt-2 uppercase">
                {agentConfig?.vector_db_type || 'N/A'}
              </p>
            </div>
          </Card>
        </div>

        {/* Agent Configuration */}
        <Card title="Agent Configuration">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Business Name</p>
              <p className="text-gray-900 mt-1">{agentConfig?.business_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">AI Persona</p>
              <p className="text-gray-900 mt-1 whitespace-pre-wrap">
                {agentConfig?.ai_persona}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Default Language</p>
              <p className="text-gray-900 mt-1">{agentConfig?.default_language.toUpperCase()}</p>
            </div>
            <Button variant="secondary" onClick={handleReloadKnowledge} isLoading={reloading}>
              <RefreshCw size={16} className="mr-2" />
              Reload Knowledge Base
            </Button>
          </div>
        </Card>

        {/* Test Message */}
        <Card title="Test AI Agent" subtitle="Send a test message to see how your AI responds">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test Message
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter a test message..."
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') handleTestMessage();
                  }}
                />
                <Button onClick={handleTestMessage} isLoading={testing}>
                  <Send size={16} className="mr-2" />
                  Send
                </Button>
              </div>
            </div>

            {/* Test Result */}
            {testResult && (
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Bot className="text-blue-600 flex-shrink-0 mt-1" size={24} />
                  <div className="flex-1">
                    <p className="text-gray-900 mb-3">{testResult.response}</p>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                      <span>
                        <strong>Language:</strong> {testResult.language_detected}
                      </span>
                      <span>
                        <strong>Confidence:</strong> {testResult.confidence}%
                      </span>
                      <span>
                        <strong>Processing Time:</strong> {testResult.processing_time_ms}ms
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Sample Messages */}
        <Card title="Sample Test Messages">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              'What are your business hours?',
              'Do you offer international shipping?',
              'How can I track my order?',
              'What payment methods do you accept?',
            ].map((message, index) => (
              <button
                key={index}
                onClick={() => setTestMessage(message)}
                className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <p className="text-sm text-gray-700">{message}</p>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
