import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { uploadsApi } from '../../api/client';
import { Upload } from '../../types';
import { 
  UploadCloud, Plus, FileText, Image as ImageIcon, 
  AlertTriangle, CheckCircle2, Clock, Eye, ArrowUpRight, Loader2 
} from 'lucide-react';

export const ContributorDashboard: React.FC = () => {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    uploadsApi.getMyUploads()
      .then((data) => setUploads(data))
      .catch((err) => setError('Failed to load uploads'))
      .finally(() => setLoading(false));
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'uploaded':
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Clock className="w-3 h-3 mr-1" />
            Processing
          </span>
        );
      case 'analyzed':
      case 'published':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Analyzed
          </span>
        );
      case 'flagged':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Flagged for Review
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading contributor workspace...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Contributor Dashboard</h1>
          <p className="text-slate-600 text-sm mt-0.5">
            Manage your uploaded datasets, view pre-check results, AI trust scores, and earnings.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/contributor/earnings"
            className="inline-flex items-center space-x-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold text-sm px-4 py-2.5 rounded-lg transition-colors"
          >
            <span>My Earnings & Payouts</span>
            <ArrowUpRight className="h-4 w-4" />
          </Link>
          <Link
            to="/contributor/upload"
            className="inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-sm transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Upload Dataset</span>
          </Link>
        </div>

      </div>

      {error && (
        <div className="mb-6 bg-red-50 text-red-700 p-4 rounded-lg text-sm border border-red-200">
          {error}
        </div>
      )}

      {/* Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Uploads</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{uploads.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pre-checks Passed</p>
          <p className="text-2xl font-bold text-emerald-600 mt-1">
            {uploads.filter((u) => u.status !== 'flagged' && u.status !== 'rejected').length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Flags / Moderation</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {uploads.filter((u) => u.status === 'flagged').length}
          </p>
        </div>
      </div>

      {/* Uploads List */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <h2 className="text-base font-bold text-slate-900">Your Uploaded Datasets</h2>
          <span className="text-xs text-slate-500">{uploads.length} items</span>
        </div>

        {uploads.length === 0 ? (
          <div className="p-12 text-center">
            <UploadCloud className="h-12 w-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">No datasets uploaded yet</h3>
            <p className="text-slate-500 text-sm mt-1 mb-4">
              Upload your first image or tabular dataset to get started with AI evaluation.
            </p>
            <Link
              to="/contributor/upload"
              className="inline-flex items-center space-x-1.5 bg-indigo-600 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              <span>Upload Dataset</span>
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {uploads.map((upload) => (
              <div
                key={upload.id}
                className="p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-slate-50/75 transition-colors"
              >
                <div className="flex items-start space-x-3.5">
                  <div className="p-2.5 rounded-lg bg-slate-100 text-slate-600 flex-shrink-0 mt-0.5">
                    {upload.file_info?.data_type === 'image' ? (
                      <ImageIcon className="h-5 w-5 text-indigo-600" />
                    ) : (
                      <FileText className="h-5 w-5 text-emerald-600" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center space-x-2">
                      <Link
                        to={`/contributor/uploads/${upload.id}`}
                        className="text-base font-bold text-slate-900 hover:text-indigo-600 transition-colors"
                      >
                        {upload.title}
                      </Link>
                      {getStatusBadge(upload.status)}
                    </div>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-1 max-w-xl">
                      {upload.description}
                    </p>
                    <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1.5 font-mono">
                      <span>ID: #{upload.id}</span>
                      <span>•</span>
                      <span>{upload.file_info?.data_type?.toUpperCase()}</span>
                      <span>•</span>
                      <span>{((upload.file_info?.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
                      <span>•</span>
                      <span>{new Date(upload.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-end sm:self-center">
                  <Link
                    to={`/contributor/uploads/${upload.id}`}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-indigo-600 transition-colors"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>View Details</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
