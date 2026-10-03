import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi, formatErrorMessage } from '../api/client';
import { consentApi } from '../features/consent/api';
import { ConsentDocument } from '../features/consent/types';
import { ConsentCheckbox } from '../features/consent/ConsentCheckbox';
import { Role } from '../types';
import { Lock, Mail, User, Building, AlertCircle, Database, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('contributor');
  const [displayName, setDisplayName] = useState('');
  const [companyName, setCompanyName] = useState('');
  
  // DPDP Statutory Registration Consents (Unticked by default)
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [isAdultConfirmed, setIsAdultConfirmed] = useState(false);

  // Active documents for modal inspection
  const [activeDocs, setActiveDocs] = useState<Record<string, ConsentDocument>>({});

  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await consentApi.getActiveDocuments();
        const map: Record<string, ConsentDocument> = {};
        docs.forEach((d) => {
          map[d.purpose_code] = d;
        });
        setActiveDocs(map);
      } catch (err) {
        console.error('Failed to load active consent documents', err);
      }
    };
    fetchDocs();
  }, []);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!termsAccepted) {
      errs.terms = 'You must accept the Terms of Service to register.';
    }
    if (!privacyAccepted) {
      errs.privacy = 'You must acknowledge the Privacy Notice.';
    }
    if (!isAdultConfirmed) {
      errs.adult = 'You must confirm that you are at least 18 years old (DPDP Act Section 9).';
    }
    setErrors(errs);
    if (Object.keys(errs).length > 0) {
      setError('Please acknowledge all required DPDP regulatory consents.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

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
        terms_accepted: true,
        privacy_accepted: true,
        is_adult_confirmed: true,
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
      <div className="max-w-xl w-full space-y-8 bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
        <div className="text-center">
          <div className="inline-flex p-3 rounded-2xl bg-indigo-50 text-indigo-600 mb-3 shadow-sm">
            <Database className="h-8 w-8" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Create an Account</h2>
          <p className="mt-2 text-xs text-slate-600">
            Join the React n Data two-sided data marketplace under India's DPDP Act 2023 compliance framework
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center space-x-2 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">I want to join as</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('contributor')}
                  className={`py-2 px-3 text-xs font-semibold rounded-xl border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'contributor'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <User className="h-4 w-4" />
                  <span>Contributor</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('agency')}
                  className={`py-2 px-3 text-xs font-semibold rounded-xl border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'agency'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <Building className="h-4 w-4" />
                  <span>Agency Buyer</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('admin')}
                  className={`py-2 px-3 text-xs font-semibold rounded-xl border flex flex-col items-center justify-center space-y-1 transition-all ${
                    role === 'admin'
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <ShieldCheck className="h-4 w-4" />
                  <span>Admin</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            {role === 'contributor' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Display Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs"
                    placeholder="e.g. DataScientistJane"
                  />
                </div>
              </div>
            )}

            {role === 'agency' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Agency Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Building className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs"
                    placeholder="e.g. Apex Analytics Inc."
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>

          {/* DPDP Compliance & Consent Section */}
          <div className="pt-2 border-t border-slate-100 space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              Statutory Consents (DPDP Act, 2023)
            </h3>

            {/* Terms of Service */}
            <ConsentCheckbox
              id="terms_accepted"
              checked={termsAccepted}
              onChange={setTermsAccepted}
              label="Platform Terms of Service"
              summary="I agree to the platform rules, intermediary obligations, payment settlement guidelines, and 80/20 ledger terms."
              document={activeDocs['terms_of_service']}
              documentPurposeCode="terms_of_service"
              required={true}
              error={errors.terms}
            />

            {/* Privacy Notice */}
            <ConsentCheckbox
              id="privacy_accepted"
              checked={privacyAccepted}
              onChange={setPrivacyAccepted}
              label="Privacy Notice & Fiduciary Disclosures"
              summary="I acknowledge the collection, processing, and retention of personal data as specified under Section 5 DPDP Act."
              document={activeDocs['privacy_notice']}
              documentPurposeCode="privacy_notice"
              required={true}
              error={errors.privacy}
            />

            {/* Age Verification (18+) */}
            <div className={`flex items-start gap-3 p-3.5 rounded-xl border transition ${
              isAdultConfirmed
                ? 'bg-blue-50/40 border-blue-200'
                : errors.adult
                ? 'bg-red-50/30 border-red-200'
                : 'bg-white border-slate-200 hover:border-slate-300'
            }`}>
              <div className="flex items-center h-5 mt-0.5">
                <input
                  id="is_adult_confirmed"
                  type="checkbox"
                  checked={isAdultConfirmed}
                  onChange={(e) => setIsAdultConfirmed(e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-white border-slate-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                />
              </div>
              <div className="flex-1 text-xs">
                <label htmlFor="is_adult_confirmed" className="font-semibold text-slate-900 cursor-pointer flex items-center gap-1.5">
                  Age Confirmation (18+ Years)
                  <span className="text-red-500 font-bold">*</span>
                </label>
                <p className="text-slate-600 mt-0.5 leading-relaxed text-[11px]">
                  I confirm that I am at least 18 years of age. I understand that processing of personal data belonging to children without verifiable parental consent is prohibited under Section 9 of India's DPDP Act, 2023.
                </p>
                {errors.adult && <p className="text-red-600 font-medium mt-1 text-[11px]">{errors.adult}</p>}
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Registering with DPDP verification...' : 'Create Account & Agree to Consents'}
          </button>
        </form>

        {/* Grievance Officer Notice */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-500 space-y-1">
          <p className="font-semibold text-slate-700">Data Protection & Grievance Redressal</p>
          <p>
            Designated Grievance Officer: <span className="text-slate-700 font-medium">Grievance Redressal Cell</span> • Email:{' '}
            <a href="mailto:grievance@reactndata.internal" className="text-indigo-600 hover:underline font-medium">
              grievance@reactndata.internal
            </a>
          </p>
        </div>

        <div className="text-center text-xs text-slate-600 pt-2 border-t border-slate-100">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
