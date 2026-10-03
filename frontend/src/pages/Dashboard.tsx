import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { UploadCloud, Store, Shield, UserCheck, ArrowRight } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 mb-8">
        <div className="flex items-center space-x-3 text-indigo-600 mb-2">
          <UserCheck className="h-6 w-6" />
          <span className="text-sm font-semibold uppercase tracking-wider">Welcome Back</span>
        </div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          {user ? `Hello, ${user.email}` : 'Welcome to React n Data'}
        </h1>
        <p className="text-slate-600 max-w-2xl">
          A two-sided AI-scored data marketplace. Datasets undergo domain classification, trust scoring (0-100), and pricing recommendations powered by AI pre-checks and Gemma model rules.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between hover:border-indigo-300 transition-colors">
          <div>
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg w-fit mb-4">
              <UploadCloud className="h-6 w-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-1">Contributor Portal</h2>
            <p className="text-sm text-slate-600 mb-4">
              Upload image and tabular datasets, view AI trust scores, adjust pricing, and request custom category changes.
            </p>
          </div>
          <Link
            to="/contributor/dashboard"
            className="inline-flex items-center text-sm font-semibold text-indigo-600 hover:text-indigo-700 space-x-1"
          >
            <span>Go to Contributor Portal</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between hover:border-indigo-300 transition-colors">
          <div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg w-fit mb-4">
              <Store className="h-6 w-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-1">Agency Marketplace</h2>
            <p className="text-sm text-slate-600 mb-4">
              Browse domain-grouped datasets (Physics, Business, Food), inspect safe previews and trust scores, and license data.
            </p>
          </div>
          <Link
            to="/marketplace"
            className="inline-flex items-center text-sm font-semibold text-emerald-600 hover:text-emerald-700 space-x-1"
          >
            <span>Browse Marketplace</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between hover:border-indigo-300 transition-colors">
          <div>
            <div className="p-3 bg-amber-50 text-amber-600 rounded-lg w-fit mb-4">
              <Shield className="h-6 w-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-1">Admin Panel</h2>
            <p className="text-sm text-slate-600 mb-4">
              Moderate flagged uploads, resolve category mismatch reviews, manage category taxonomy, and audit platform revenue.
            </p>
          </div>
          <Link
            to="/admin/moderation"
            className="inline-flex items-center text-sm font-semibold text-amber-600 hover:text-amber-700 space-x-1"
          >
            <span>Open Admin Panel</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
};
