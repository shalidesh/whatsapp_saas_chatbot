'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { Business } from '@/types';
import { Save } from 'lucide-react';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const { selectedBusiness, setSelectedBusiness } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    website_url: '',
    whatsapp_phone_number: '',
    business_category: '',
    ai_persona: '',
    default_language: 'en',
    supported_languages: ['en', 'si'],
  });

  useEffect(() => {
    if (selectedBusiness) {
      loadBusinessSettings();
    }
  }, [selectedBusiness]);

  const loadBusinessSettings = async () => {
    if (!selectedBusiness) return;

    try {
      setLoading(true);
      const data = await apiClient.getBusinessSettings(selectedBusiness.id);
      const business = data.business;
      setFormData({
        name: business.name || '',
        description: business.description || '',
        website_url: business.website_url || '',
        whatsapp_phone_number: business.whatsapp_phone_number || '',
        business_category: business.business_category || '',
        ai_persona: business.ai_persona || '',
        default_language: business.default_language || 'en',
        supported_languages: business.supported_languages || ['en', 'si'],
      });
    } catch (error) {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedBusiness) return;

    try {
      setSaving(true);
      const response = await apiClient.updateBusinessSettings({
        business_id: selectedBusiness.id,
        ...formData,
      });
      setSelectedBusiness(response.business);
      toast.success('Settings updated successfully');
    } catch (error) {
      toast.error('Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleLanguageToggle = (lang: string) => {
    if (formData.supported_languages.includes(lang)) {
      setFormData({
        ...formData,
        supported_languages: formData.supported_languages.filter((l) => l !== lang),
      });
    } else {
      setFormData({
        ...formData,
        supported_languages: [...formData.supported_languages, lang],
      });
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
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">Manage your business configuration</p>
          </div>
          <Button onClick={handleSave} isLoading={saving}>
            <Save size={16} className="mr-2" />
            Save Changes
          </Button>
        </div>

        {/* Business Information */}
        <Card title="Business Information">
          <div className="space-y-4">
            <Input
              label="Business Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="My Business"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Describe your business"
              />
            </div>

            <Input
              label="Website URL"
              type="url"
              value={formData.website_url}
              onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
              placeholder="https://example.com"
            />

            <Input
              label="WhatsApp Phone Number"
              type="tel"
              value={formData.whatsapp_phone_number}
              onChange={(e) =>
                setFormData({ ...formData, whatsapp_phone_number: e.target.value })
              }
              placeholder="+1234567890"
            />

            <Input
              label="Business Category"
              value={formData.business_category}
              onChange={(e) => setFormData({ ...formData, business_category: e.target.value })}
              placeholder="E.g., E-commerce, Healthcare, Education"
            />
          </div>
        </Card>

        {/* AI Configuration */}
        <Card title="AI Agent Configuration">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                AI Persona
              </label>
              <textarea
                value={formData.ai_persona}
                onChange={(e) => setFormData({ ...formData, ai_persona: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                placeholder="Define how your AI agent should behave..."
              />
              <p className="text-xs text-gray-500 mt-1">
                Describe your AI agent's personality and how it should interact with customers
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Supported Languages
              </label>
              <div className="flex flex-wrap gap-2">
                {['en', 'si', 'ta', 'es', 'fr'].map((lang) => (
                  <button
                    key={lang}
                    onClick={() => handleLanguageToggle(lang)}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      formData.supported_languages.includes(lang)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {lang.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Language
              </label>
              <select
                value={formData.default_language}
                onChange={(e) => setFormData({ ...formData, default_language: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {formData.supported_languages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {/* Save Button (Mobile) */}
        <div className="lg:hidden">
          <Button onClick={handleSave} isLoading={saving} className="w-full">
            <Save size={16} className="mr-2" />
            Save Changes
          </Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
