import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi, formatErrorMessage } from '../api/client';
import { Role } from '../types';
import { Lock, Mail, User, Building, AlertCircle, Database, ShieldCheck } from 'lucide-react';

export const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('contributor');
  const [displayName, setDisplayName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const cleanEmail = email.trim();
    const cleanDisplayName = displayName.trim();
    const cleanCompanyName = companyName.trim();

    try {
      await authApi.register({
        email: cleanEmail,
        password,
        role,
        display_name: role === 'contributor' ? (cleanDisplayName || undefined) : undefined,
        company_name: role === 'agency' ? (cleanCompanyName || undefined) : undefined,
      });

      // Auto-login after registration
      const tokenRes = await authApi.login({ email: cleanEmail, password });
      await login(tokenRes.access_token, tokenRes.refresh_token);

      if (role === 'contributor') {
        navigate('/contributor/dashboard');
      } else if (role === 'agency') {
        navigate('/marketplace');
      } else if (role === 'admin') {
        navigate('/admin/moderation');
      } else {
        navigate('/');
      }
    } catch (err: any) {
      setError(formatErrorMessage(err, 'Registration failed. Please check your inputs.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div className="text-center">
          <div className="inline-flex p-3 rounded-full bg-indigo-50 text-indigo-600 mb-3">
            <Database className="h-8 w-8" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Create an Account</h2>
          <p className="mt-2 text-sm text-slate-600">
            Join the React n Data two-sided data marketplace
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center space-x-2 text-sm">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">I want to join as</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('contributor')}
                  className={`py-2 px-3 text-xs font-semibold rounded-lg border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'contributor'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <User className="h-4 w-4" />
                  <span>Contributor</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('agency')}
                  className={`py-2 px-3 text-xs font-semibold rounded-lg border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'agency'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <Building className="h-4 w-4" />
                  <span>Agency Buyer</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('admin')}
                  className={`py-2 px-3 text-xs font-semibold rounded-lg border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'admin'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <ShieldCheck className="h-4 w-4" />
                  <span>Admin</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-5 w-5" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            {role === 'contributor' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Display Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="h-5 w-5" />
                  </div>
                  <input
                    type="text"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                    placeholder="e.g. DataScientistJane"
                  />
                </div>
              </div>
            )}

            {role === 'agency' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Company / Agency Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Building className="h-5 w-5" />
                  </div>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                    placeholder="e.g. Apex Analytics Inc."
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-5 w-5" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="text-center text-sm text-slate-600 pt-4 border-t border-slate-100">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
