import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, AlertCircle, Package } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import BrandLogo from '../components/BrandLogo.jsx';

function PacfullyLogo({ size = 'md' }) {
  return <BrandLogo width={size === 'lg' ? 180 : 142} />;
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function Login() {
  const navigate             = useNavigate();
  const { login, loginWithGoogle, isLoggedIn } = useAuth();
  const googleButtonRef = useRef(null);
  const googleInitializedRef = useRef(false);

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState('');

  // If already logged in, redirect — use useEffect to avoid render-phase navigation
  useEffect(() => {
    if (isLoggedIn) {
      navigate('/dashboard', { replace: true });
    }
  }, [isLoggedIn, navigate]);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const renderGoogleButton = () => {
      if (googleInitializedRef.current || !window.google?.accounts?.id || !googleButtonRef.current) return;
        if (!window.__pacfullyGoogleInitialized) {
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: async ({ credential }) => {
              setLoading(true);
              setError('');
              const errMsg = await loginWithGoogle(credential);
              setLoading(false);
              if (errMsg) setError(errMsg);
              else navigate('/dashboard', { replace: true });
            },
          });
          window.__pacfullyGoogleInitialized = true;
        }
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rect',
        logo_alignment: 'left',
        width: googleButtonRef.current.clientWidth,
      });
      googleInitializedRef.current = true;
    };

    const scriptUrl = 'https://accounts.google.com/gsi/client';
    const existingScript = document.querySelector(`script[src="${scriptUrl}"]`);
    if (existingScript) {
      if (window.google?.accounts?.id) renderGoogleButton();
      else existingScript.addEventListener('load', renderGoogleButton, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = scriptUrl;
    script.async = true;
    script.defer = true;
    script.onload = renderGoogleButton;
    document.head.appendChild(script);
  }, [loginWithGoogle, navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Enter your email address and password to sign in.');
      return;
    }
    if (!e.currentTarget.checkValidity()) {
      setError('Enter a valid email address.');
      return;
    }
    setLoading(true);
    setError('');

    const errMsg = await login(email, password);

    setLoading(false);
    if (errMsg) {
      setError(errMsg);
    } else {
      // login() set the token in context → useEffect above fires → navigate to /dashboard
      navigate('/dashboard', { replace: true });
    }
  };

  // Don't render the form while redirecting
  if (isLoggedIn) return null;

  return (
    <div className="login-layout" style={{ minHeight: '100vh' }}>

      {/* ── Left: Form ──────────────────────────────────── */}
      <div className="login-form-panel" style={{
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        background: '#fff',
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>

          {/* Logo */}
          <div style={{ marginBottom: 36, textAlign: 'center' }}>
            <PacfullyLogo size="lg" />
          </div>

          <h1 style={{ fontFamily: 'Manrope', fontSize: 28, fontWeight: 800, color: '#1A1D23', textAlign: 'center', margin: '0 0 6px' }}>
            Welcome Back
          </h1>
          <p style={{ fontSize: 13, color: '#6B7280', textAlign: 'center', margin: '0 0 28px' }}>
            Sign in to your Cost Intelligence Platform
          </p>

          {/* Form */}
          <form noValidate onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Error banner */}
            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '10px 14px', background: '#FFF5F5',
                border: '1px solid #FED7D7', borderRadius: 7,
                fontSize: 13, color: '#C53030',
              }}>
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                {error}
              </div>
            )}

            {/* Email */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label htmlFor="login-email" style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', letterSpacing: '0.02em' }}>
                Email address
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="you@company.com"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                style={{
                  height: 40, border: '1px solid #E5E9EE', borderRadius: 7,
                  padding: '0 12px', fontSize: 13, outline: 'none',
                  fontFamily: 'Inter, sans-serif',
                  transition: 'border 0.15s',
                }}
                onFocus={e => e.target.style.borderColor = '#FF5A3A'}
                onBlur={e  => e.target.style.borderColor = '#E5E9EE'}
              />
            </div>

            {/* Password */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label htmlFor="login-password" style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', letterSpacing: '0.02em' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  type={showPass ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError(''); }}
                  style={{
                    height: 40, width: '100%', border: '1px solid #E5E9EE', borderRadius: 7,
                    padding: '0 40px 0 12px', fontSize: 13, outline: 'none',
                    fontFamily: 'Inter, sans-serif', boxSizing: 'border-box',
                    transition: 'border 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = '#FF5A3A'}
                  onBlur={e  => e.target.style.borderColor = '#E5E9EE'}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(v => !v)}
                  style={{
                    position: 'absolute', right: 11, top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none', border: 'none',
                    color: '#9CA3AF', cursor: 'pointer', padding: 0,
                  }}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Remember + Forgot */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', fontSize: 13 }}>
                <input
                  type="checkbox" checked={remember}
                  onChange={e => setRemember(e.target.checked)}
                  style={{ accentColor: '#FF5A3A', width: 15, height: 15 }}
                />
                Remember me
              </label>
              <button type="button" style={{
                background: 'none', border: 'none', color: '#FF5A3A',
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }} onClick={() => setError('Password resets are managed by your Pacfully administrator. Contact your account administrator for help.')}>
                Forgot password?
              </button>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              style={{
                height: 44,
                background: loading ? '#FFB09C' : '#FF5A3A',
                color: '#fff', border: 'none', borderRadius: 8,
                fontSize: 14, fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 14px rgba(255,90,58,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                transition: 'background 0.2s', fontFamily: 'Inter, sans-serif',
              }}
            >
              {loading ? (
                <>
                  <span style={{
                    width: 16, height: 16,
                    border: '2px solid rgba(255,255,255,0.35)',
                    borderTopColor: '#fff', borderRadius: '50%',
                    display: 'inline-block', animation: 'pac-spin 0.7s linear infinite',
                  }} />
                  Signing in…
                </>
              ) : (
                <>Sign in <ArrowRight size={15} /></>
              )}
            </button>
          </form>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '20px 0' }}>
            <div style={{ flex: 1, height: 1, background: '#E5E9EE' }} />
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>or continue with</span>
            <div style={{ flex: 1, height: 1, background: '#E5E9EE' }} />
          </div>

          <div ref={googleButtonRef} style={{ display: 'flex', justifyContent: 'center', minHeight: 44 }}>
            {!GOOGLE_CLIENT_ID && (
              <button type="button" onClick={() => setError('Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID in the frontend environment.')}
                style={{
                  width: '100%', height: 44, background: '#fff',
                  border: '1px solid #E5E9EE', borderRadius: 8,
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 10, color: '#434950', fontFamily: 'Inter, sans-serif',
                }}>
                <svg width="16" height="16" viewBox="0 0 18 18">
                  <path fill="#4285F4" d="M17.64 9.2a10 10 0 0 0-.16-1.7H9v3.22h4.84A4.14 4.14 0 0 1 12.07 13v2.22h2.89A8.78 8.78 0 0 0 17.64 9.2z"/>
                  <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.89-2.24a5.4 5.4 0 0 1-8.05-2.85H.94v2.3A9 9 0 0 0 9 18z"/>
                  <path fill="#FBBC05" d="M4.02 10.73A5.4 5.4 0 0 1 3.74 9c0-.61.1-1.2.28-1.73V4.97H.94A9 9 0 0 0 0 9c0 1.45.35 2.82.94 4.03z"/>
                  <path fill="#EA4335" d="M9 3.58a4.86 4.86 0 0 1 3.44 1.35l2.58-2.58A8.64 8.64 0 0 0 9 0 9 9 0 0 0 .94 4.97l3.08 2.3A5.36 5.36 0 0 1 9 3.58z"/>
                </svg>
                Sign in with Google
              </button>
            )}
          </div>

          <p style={{ textAlign: 'center', fontSize: 12, color: '#9CA3AF', marginTop: 24 }}>
            New to Pacfully?{' '}
            <button type="button" onClick={() => window.open('https://pacfully.com/contact', '_blank', 'noopener,noreferrer')} style={{ background: 'none', border: 'none', color: '#FF5A3A', fontWeight: 600, cursor: 'pointer', fontSize: 12 }}>
              Contact Admin
            </button>
          </p>
        </div>
      </div>

      {/* ── Right: Brand Panel ──────────────────────────── */}
      <div className="login-brand-panel" style={{
        background: 'linear-gradient(160deg, #FF7A5C 0%, #FF5A3A 40%, #CC3C22 100%)',
        flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        padding: 48, position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: -80, right: -80, width: 300, height: 300, borderRadius: '50%', background: 'rgba(255,255,255,0.07)' }} />
        <div style={{ position: 'absolute', bottom: -60, left: -60, width: 240, height: 240, borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }} />

          <div style={{
          width: 220, height: 190, background: 'rgba(255,255,255,0.15)',
          borderRadius: 20, marginBottom: 36,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.25)',
          position: 'relative',
        }}>
          <Package size={70} color="rgba(255,255,255,0.9)" />
          <BrandLogo width={150} style={{ position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)', background: '#fff', padding: 4, borderRadius: 2 }} />
        </div>

        <h2 style={{ fontFamily: 'Manrope', fontSize: 30, fontWeight: 800, color: '#fff', textAlign: 'center', margin: '0 0 12px' }}>
          Smart Packaging
        </h2>
        <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.85)', textAlign: 'center', fontWeight: 600, marginBottom: 36 }}>
          Smarter Business
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', maxWidth: 280 }}>
          {['AI-powered layout extraction', 'Module-wise cost traceability', 'Instant quotation generation'].map(f => (
            <div key={f} style={{
              background: 'rgba(255,255,255,0.18)', borderRadius: 8,
              padding: '10px 14px', fontSize: 13, color: '#fff', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff', flexShrink: 0 }} />
              {f}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 32, width: '100%', maxWidth: 280 }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.6)', marginBottom: 8 }}>
            Need an account?
          </p>
          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', margin: 0 }}>
            Ask your Pacfully administrator to create your sign-in.
          </p>
        </div>
      </div>

      {/* Spinner keyframe */}
      <style>{`@keyframes pac-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
