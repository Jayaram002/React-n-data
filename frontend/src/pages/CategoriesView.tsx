import React, { useEffect, useState } from 'react';
import { categoriesApi } from '../api/client';
import { CategoryTree } from '../types';
import { Layers, Tag, DollarSign, Loader2 } from 'lucide-react';

export const CategoriesView: React.FC = () => {
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    categoriesApi.getCategories()
      .then((data) => setCategories(data))
      .catch((err) => setError('Failed to load category taxonomy'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading domain taxonomy...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <Layers className="h-6 w-6 text-indigo-600" />
          <span>Category Taxonomy & Base Prices</span>
        </h1>
        <p className="text-slate-600 text-sm mt-1">
          Explore the hierarchical dataset domains. Every domain defines base pricing and subcategory classifications.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg text-sm mb-6 border border-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map((domain) => (
          <div
            key={domain.id}
            className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between hover:shadow-md transition-shadow"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded border border-indigo-100">
                  Domain
                </span>
                <span className="text-xs font-semibold text-slate-500 flex items-center">
                  <DollarSign className="h-3.5 w-3.5 text-slate-400" />
                  {(domain.base_price_paise / 100).toFixed(2)} Base
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-1">{domain.name}</h2>
              <p className="text-xs text-slate-400 font-mono mb-4">slug: {domain.slug}</p>

              <div className="border-t border-slate-100 pt-3">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1">
                  <Tag className="h-3.5 w-3.5" />
                  <span>Subcategories ({domain.subcategories.length})</span>
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {domain.subcategories.map((sub) => (
                    <span
                      key={sub.id}
                      className="inline-flex items-center text-xs font-medium bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md"
                    >
                      {sub.name}
                      <span className="ml-1 text-[10px] text-slate-400">
                        (${(sub.base_price_paise / 100).toFixed(0)})
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
