import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [mode, setMode]         = useState('login'); // 'login' | 'register'
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password);
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(
        mode === 'login'
          ? 'Invalid email or password.'
          : 'Could not create account — email may already be in use.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <div style={styles.logoDot} />
          <div>
            <div style={styles.brandTitle}>GLP-1</div>
            <div style={styles.brandSubtitle}>ANALYTICS</div>
          </div>
        </div>

        <h1 style={styles.heading}>
          {mode === 'login' ? 'Sign in' : 'Create an account'}
        </h1>
        <p style={styles.subheading}>
          GLP-1 Adherence &amp; Cost Intelligence Platform
        </p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
              placeholder="you@company.com"
              autoComplete="email"
            />
          </label>

          <label style={styles.label}>
            Password
            <input
              type="password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              placeholder="••••••••"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" disabled={loading} style={styles.submitBtn}>
            {loading
              ? 'Please wait…'
              : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <div style={styles.switchRow}>
          {mode === 'login' ? (
            <>
              Don&apos;t have an account?{' '}
              <button style={styles.linkBtn} onClick={() => setMode('register')}>
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button style={styles.linkBtn} onClick={() => setMode('login')}>
                Sign in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f4f6f9',
    fontFamily: 'inherit',
  },
  card: {
    width: 380,
    background: '#ffffff',
    borderRadius: 12,
    padding: '40px 36px',
    boxShadow: '0 4px 24px rgba(20, 30, 50, 0.08)',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 28,
  },
  logoDot: {
    width: 36,
    height: 36,
    borderRadius: 8,
    background: '#2f5fd6',
  },
  brandTitle: {
    fontWeight: 700,
    fontSize: 16,
    color: '#1a2332',
    lineHeight: 1.1,
  },
  brandSubtitle: {
    fontSize: 11,
    letterSpacing: 1,
    color: '#8a93a3',
  },
  heading: {
    fontSize: 22,
    fontWeight: 700,
    color: '#1a2332',
    margin: '0 0 4px',
  },
  subheading: {
    fontSize: 13,
    color: '#8a93a3',
    margin: '0 0 24px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    fontSize: 13,
    color: '#4a5568',
    fontWeight: 500,
  },
  input: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid #dfe3ea',
    fontSize: 14,
    outline: 'none',
  },
  error: {
    background: '#fdecec',
    color: '#c0392b',
    fontSize: 13,
    padding: '8px 12px',
    borderRadius: 8,
  },
  submitBtn: {
    marginTop: 4,
    padding: '11px 0',
    borderRadius: 8,
    border: 'none',
    background: '#2f5fd6',
    color: '#fff',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  switchRow: {
    marginTop: 20,
    fontSize: 13,
    color: '#8a93a3',
    textAlign: 'center',
  },
  linkBtn: {
    background: 'none',
    border: 'none',
    color: '#2f5fd6',
    fontWeight: 600,
    cursor: 'pointer',
    padding: 0,
    fontSize: 13,
  },
};