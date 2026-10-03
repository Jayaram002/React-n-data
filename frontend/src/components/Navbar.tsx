import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Database, LogOut, User as UserIcon, Shield, Store, UploadCloud, ShoppingBag, DollarSign, BarChart3, Layers } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2 text-indigo-600 font-bold text-xl">
              <Database className="h-7 w-7" />
              <span>React n Data</span>
            </Link>
            <span className="bg-indigo-50 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded border border-indigo-200">
              MVP
            </span>
          </div>

          <div className="flex items-center space-x-6">
            <Link to="/marketplace" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
              <Store className="h-4 w-4" />
              <span>Marketplace</span>
            </Link>

            {user ? (
              <>
                {user.role === 'contributor' && (
                  <>
                    <Link to="/contributor/dashboard" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                      <UploadCloud className="h-4 w-4" />
                      <span>Uploads</span>
                    </Link>
                    <Link to="/contributor/earnings" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                      <DollarSign className="h-4 w-4 text-emerald-600" />
                      <span>Earnings</span>
                    </Link>
                  </>
                )}

                <Link to="/purchases" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                  <ShoppingBag className="h-4 w-4" />
                  <span>Purchases</span>
                </Link>

                {user.role === 'admin' && (
                  <div className="flex items-center space-x-4 pl-2 border-l border-slate-200">
                    <Link to="/admin/moderation" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                      <Shield className="h-4 w-4 text-indigo-600" />
                      <span>Moderation</span>
                    </Link>
                    <Link to="/admin/taxonomy" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                      <Layers className="h-4 w-4 text-indigo-600" />
                      <span>Taxonomy</span>
                    </Link>
                    <Link to="/admin/analytics" className="text-slate-600 hover:text-indigo-600 font-medium text-sm flex items-center space-x-1">
                      <BarChart3 className="h-4 w-4 text-indigo-600" />
                      <span>Analytics</span>
                    </Link>
                  </div>
                )}



                <div className="flex items-center space-x-3 pl-4 border-l border-slate-200">
                  <div className="flex items-center space-x-2">
                    <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600">
                      <UserIcon className="h-4 w-4" />
                    </div>
                    <div className="text-xs">
                      <p className="font-semibold text-slate-800">{user.email}</p>
                      <span className="capitalize text-slate-500 font-medium">({user.role})</span>
                    </div>
                  </div>

                  <button
                    onClick={handleLogout}
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                    title="Logout"
                  >
                    <LogOut className="h-5 w-5" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  to="/login"
                  className="text-slate-600 hover:text-slate-900 font-medium text-sm px-3 py-1.5"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm px-4 py-2 rounded-lg transition-colors shadow-sm"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};
