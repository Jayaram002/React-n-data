import React, { useEffect, useState } from 'react';
import { adminApi, categoriesApi, formatErrorMessage } from '../../api/client';
import { CategoryTree } from '../../types';
import { 
  FolderPlus, Edit3, Plus, CheckCircle2, XCircle, 
  Layers, DollarSign, Loader2, Sparkles, RefreshCw, ChevronRight 
} from 'lucide-react';

export const AdminTaxonomyPage: React.FC = () => {
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Category Modal State
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<any | null>(null);
  const [catForm, setCatForm] = useState({ name: '', slug: '', basePrice: '50.00', active: true });

  // Subcategory Modal State
  const [subModalOpen, setSubModalOpen] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<number | null>(null);
  const [editingSub, setEditingSub] = useState<any | null>(null);
  const [subForm, setSubForm] = useState({ name: '', slug: '', basePrice: '50.00', active: true });

  const [submitting, setSubmitting] = useState(false);

  const fetchTaxonomy = async () => {
    try {
      setLoading(true);
      const data = await categoriesApi.getCategories();
      setCategories(data);
    } catch (err: any) {
      setError('Failed to load taxonomy tree');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTaxonomy();
  }, []);

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const pricePaise = Math.round(parseFloat(catForm.basePrice) * 100);
      if (editingCategory) {
        await adminApi.updateCategory(editingCategory.id, {
          name: catForm.name,
          slug: catForm.slug,
          base_price_paise: pricePaise,
          active: catForm.active,
        });
        setActionSuccess(`Category '${catForm.name}' updated!`);
      } else {
        await adminApi.createCategory({
          name: catForm.name,
          slug: catForm.slug,
          base_price_paise: pricePaise,
          active: catForm.active,
        });
        setActionSuccess(`Domain category '${catForm.name}' created!`);
      }
      setCategoryModalOpen(false);
      setEditingCategory(null);
      await fetchTaxonomy();
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err: any) {
      alert(formatErrorMessage(err, 'Category save failed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubcategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedParentId) return;
    try {
      setSubmitting(true);
      const pricePaise = Math.round(parseFloat(subForm.basePrice) * 100);
      if (editingSub) {
        await adminApi.updateSubcategory(editingSub.id, {
          name: subForm.name,
          slug: subForm.slug,
          base_price_paise: pricePaise,
          active: subForm.active,
        });
        setActionSuccess(`Subcategory '${subForm.name}' updated!`);
      } else {
        await adminApi.createSubcategory({
          parent_id: selectedParentId,
          name: subForm.name,
          slug: subForm.slug,
          base_price_paise: pricePaise,
          active: subForm.active,
        });
        setActionSuccess(`Subcategory '${subForm.name}' added!`);
      }
      setSubModalOpen(false);
      setEditingSub(null);
      setSelectedParentId(null);
      await fetchTaxonomy();
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err: any) {
      alert(formatErrorMessage(err, 'Subcategory save failed'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading marketplace taxonomy system...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <Layers className="h-7 w-7 text-indigo-600" />
            <span>Taxonomy & Base Price Manager</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Maintain the marketplace domain taxonomy, subcategories, and baseline pricing algorithms.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              setEditingCategory(null);
              setCatForm({ name: '', slug: '', basePrice: '50.00', active: true });
              setCategoryModalOpen(true);
            }}
            className="inline-flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs px-4 py-2 rounded-xl shadow-sm transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Add Domain Category</span>
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="bg-emerald-50 text-emerald-800 p-4 rounded-xl text-sm font-medium border border-emerald-200 flex items-center space-x-2">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm font-medium border border-red-200">
          {error}
        </div>
      )}

      {/* Category List Accordion / Tree */}
      <div className="space-y-4">
        {categories.map((cat) => (
          <div key={cat.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Category Header */}
            <div className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60 border-b border-slate-100">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-slate-900">{cat.name}</h3>
                  <span className="text-xs font-mono text-slate-400 bg-slate-200/60 px-2 py-0.5 rounded">
                    /{cat.slug}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cat.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'}`}>
                    {cat.active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                  <span className="text-xs text-slate-400">v{cat.version}</span>
                </div>
                <div className="flex items-center space-x-3 text-xs text-slate-500">
                  <span>Base Price: <strong className="font-mono text-slate-800">${(cat.base_price_paise / 100).toFixed(2)}</strong></span>
                  <span>•</span>
                  <span>Published Datasets: <strong>{cat.published_count}</strong></span>
                  <span>•</span>
                  <span>Subcategories: <strong>{cat.subcategories.length}</strong></span>
                </div>
              </div>

              <div className="flex items-center space-x-2 self-start sm:self-auto">
                <button
                  onClick={() => {
                    setSelectedParentId(cat.id);
                    setEditingSub(null);
                    setSubForm({ name: '', slug: '', basePrice: (cat.base_price_paise / 100).toFixed(2), active: true });
                    setSubModalOpen(true);
                  }}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg transition-colors flex items-center space-x-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Subcategory</span>
                </button>

                <button
                  onClick={() => {
                    setEditingCategory(cat);
                    setCatForm({
                      name: cat.name,
                      slug: cat.slug,
                      basePrice: (cat.base_price_paise / 100).toFixed(2),
                      active: cat.active,
                    });
                    setCategoryModalOpen(true);
                  }}
                  className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition-colors"
                  title="Edit Category"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Subcategories Grid */}
            <div className="p-4 bg-white">
              {cat.subcategories.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No subcategories defined.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {cat.subcategories.map((sub) => (
                    <div
                      key={sub.id}
                      className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs hover:border-slate-200 transition-colors"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-1.5">
                          <span className="font-bold text-slate-800">{sub.name}</span>
                          <span className="text-[10px] text-slate-400 font-mono">/{sub.slug}</span>
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          ${(sub.base_price_paise / 100).toFixed(2)} • {sub.published_count} listings
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          setSelectedParentId(cat.id);
                          setEditingSub(sub);
                          setSubForm({
                            name: sub.name,
                            slug: sub.slug,
                            basePrice: (sub.base_price_paise / 100).toFixed(2),
                            active: sub.active,
                          });
                          setSubModalOpen(true);
                        }}
                        className="p-1 text-slate-400 hover:text-indigo-600 rounded transition-colors"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* CATEGORY MODAL */}
      {categoryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                {editingCategory ? `Edit Category: ${editingCategory.name}` : 'Create New Domain Category'}
              </h3>
              <button
                onClick={() => setCategoryModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCategorySubmit} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Category Name</label>
                <input
                  type="text"
                  value={catForm.name}
                  onChange={(e) => setCatForm({
                    ...catForm,
                    name: e.target.value,
                    slug: catForm.slug || e.target.value.toLowerCase().replace(/[^a-z0-9]/g, '-')
                  })}
                  placeholder="e.g. Physics & Cosmology"
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">URL Slug</label>
                <input
                  type="text"
                  value={catForm.slug}
                  onChange={(e) => setCatForm({ ...catForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                  placeholder="physics-cosmology"
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Base Price (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  value={catForm.basePrice}
                  onChange={(e) => setCatForm({ ...catForm, basePrice: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="catActive"
                  checked={catForm.active}
                  onChange={(e) => setCatForm({ ...catForm, active: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="catActive" className="text-slate-700 font-bold">Category is Active in Marketplace</label>
              </div>

              <div className="pt-3 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setCategoryModalOpen(false)}
                  className="px-4 py-2 text-slate-600 font-bold hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow flex items-center space-x-1.5"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  <span>Save Category</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SUBCATEGORY MODAL */}
      {subModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                {editingSub ? `Edit Subcategory: ${editingSub.name}` : 'Add New Subcategory'}
              </h3>
              <button
                onClick={() => setSubModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubcategorySubmit} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Subcategory Name</label>
                <input
                  type="text"
                  value={subForm.name}
                  onChange={(e) => setSubForm({
                    ...subForm,
                    name: e.target.value,
                    slug: subForm.slug || e.target.value.toLowerCase().replace(/[^a-z0-9]/g, '-')
                  })}
                  placeholder="e.g. Astrophysics Spectrum"
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Subcategory Slug</label>
                <input
                  type="text"
                  value={subForm.slug}
                  onChange={(e) => setSubForm({ ...subForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                  placeholder="astrophysics-spectrum"
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Base Price (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  value={subForm.basePrice}
                  onChange={(e) => setSubForm({ ...subForm, basePrice: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="subActive"
                  checked={subForm.active}
                  onChange={(e) => setSubForm({ ...subForm, active: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="subActive" className="text-slate-700 font-bold">Subcategory is Active</label>
              </div>

              <div className="pt-3 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setSubModalOpen(false)}
                  className="px-4 py-2 text-slate-600 font-bold hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow flex items-center space-x-1.5"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  <span>Save Subcategory</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
