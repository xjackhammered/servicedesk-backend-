import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Field from '../components/Field';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    const next = {};
    if (!form.username.trim()) next.username = 'Enter your username.';
    if (!form.password) next.password = 'Enter your password.';
    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    setFormError('');
    try {
      await signIn(form.username.trim(), form.password);
      navigate(location.state?.from?.pathname || '/', { replace: true });
    } catch (err) {
      setFormError(err.status === 401 ? 'Incorrect username or password.' : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>Sign in</h1>
        <p className="muted">Track and manage service requests in real time.</p>
        {formError && <div className="alert alert-error" role="alert">{formError}</div>}
        <Field label="Username" htmlFor="username" error={errors.username}>
          <input id="username" autoComplete="username" value={form.username} onChange={set('username')} autoFocus />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password}>
          <input id="password" type="password" autoComplete="current-password" value={form.password} onChange={set('password')} />
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="muted center">
          New operator? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </div>
  );
}
