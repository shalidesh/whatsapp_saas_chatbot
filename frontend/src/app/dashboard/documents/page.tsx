'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { Document } from '@/types';
import { format } from 'date-fns';
import { Upload, FileText, Link as LinkIcon, X } from 'lucide-react';
import toast from 'react-hot-toast';

export default function DocumentsPage() {
  const { selectedBusiness } = useAuthStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadType, setUploadType] = useState<'file' | 'url'>('file');
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState('');
  const [documentType, setDocumentType] = useState('pdf');

  useEffect(() => {
    if (selectedBusiness) {
      loadDocuments();
    }
  }, [selectedBusiness]);

  const loadDocuments = async () => {
    if (!selectedBusiness) return;

    try {
      setLoading(true);
      const data = await apiClient.getDocuments(selectedBusiness.id);
      setDocuments(data.documents);
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedBusiness) return;
    if (uploadType === 'file' && !selectedFile) {
      toast.error('Please select a file');
      return;
    }
    if (uploadType === 'url' && !urlInput) {
      toast.error('Please enter a URL');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('business_id', selectedBusiness.id.toString());
      formData.append('document_type', documentType);

      if (uploadType === 'file' && selectedFile) {
        formData.append('file', selectedFile);
      } else if (uploadType === 'url') {
        formData.append('url', urlInput);
      }

      await apiClient.uploadDocument(formData);
      toast.success('Document uploaded successfully');
      setShowUploadModal(false);
      setSelectedFile(null);
      setUrlInput('');
      loadDocuments();
    } catch (error) {
      toast.error('Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
            <p className="text-gray-600 mt-1">Manage your knowledge base content</p>
          </div>
          <Button onClick={() => setShowUploadModal(true)}>
            <Upload size={16} className="mr-2" />
            Upload Document
          </Button>
        </div>

        {/* Documents Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : documents.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <FileText className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-500 mb-4">No documents uploaded yet</p>
              <Button onClick={() => setShowUploadModal(true)}>
                <Upload size={16} className="mr-2" />
                Upload Your First Document
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {documents.map((doc) => (
              <Card key={doc.id} className="hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <FileText className="text-blue-600" size={32} />
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      doc.status === 'processed'
                        ? 'bg-green-100 text-green-800'
                        : doc.status === 'processing'
                        ? 'bg-yellow-100 text-yellow-800'
                        : doc.status === 'failed'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {doc.status}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2 truncate">
                  {doc.title || doc.file_path || doc.url}
                </h3>
                <p className="text-sm text-gray-600 mb-2">Type: {doc.document_type}</p>
                {doc.chunk_count && (
                  <p className="text-sm text-gray-600 mb-2">Chunks: {doc.chunk_count}</p>
                )}
                <p className="text-xs text-gray-500">
                  {format(new Date(doc.created_at), 'MMM dd, yyyy')}
                </p>
                {doc.error_message && (
                  <p className="text-xs text-red-500 mt-2">{doc.error_message}</p>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* Upload Modal */}
        {showUploadModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Upload Document</h2>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Upload Type Selector */}
                <div className="flex gap-2">
                  <button
                    onClick={() => setUploadType('file')}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      uploadType === 'file'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    <FileText size={16} className="inline mr-2" />
                    File
                  </button>
                  <button
                    onClick={() => setUploadType('url')}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      uploadType === 'url'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    <LinkIcon size={16} className="inline mr-2" />
                    URL
                  </button>
                </div>

                {/* Document Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Document Type
                  </label>
                  <select
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="pdf">PDF</option>
                    <option value="text">Text</option>
                    <option value="website">Website</option>
                    <option value="spreadsheet">Spreadsheet</option>
                  </select>
                </div>

                {/* File Upload */}
                {uploadType === 'file' ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select File
                    </label>
                    <input
                      type="file"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      accept=".pdf,.txt,.csv,.xlsx"
                    />
                    {selectedFile && (
                      <p className="text-sm text-gray-600 mt-2">{selectedFile.name}</p>
                    )}
                  </div>
                ) : (
                  <Input
                    label="URL"
                    type="url"
                    placeholder="https://example.com"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                  />
                )}

                <div className="flex gap-3 pt-4">
                  <Button
                    variant="secondary"
                    className="flex-1"
                    onClick={() => setShowUploadModal(false)}
                  >
                    Cancel
                  </Button>
                  <Button className="flex-1" onClick={handleFileUpload} isLoading={uploading}>
                    Upload
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
