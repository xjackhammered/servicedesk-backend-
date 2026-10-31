import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { register } from '../api/endpoints';
import Field from '../components/Field';
import { useAuth } from '../context/AuthContext';
import { validateRegisterForm } from '../utils/validation';

export default function RegisterPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    const clientErrors = validateRegisterForm(form);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    setBusy(true);
    setFormError('');
    try {
      await register({ username: form.username.trim(), email: form.email.trim(), password: form.password });
      await signIn(form.username.trim(), form.password);
      navigate('/', { replace: true });
    } catch (err) {
      if (err.status === 400 && err.details) {
        // Map server-side field errors (arrays of strings) onto the form.
        const serverErrors = {};
        Object.entries(err.details).forEach(([field, msgs]) => {
          serverErrors[field] = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
        });
        setErrors(serverErrors);
      } else {
        setFormError(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>Create operator account</h1>
        <p className="muted">Supervisor accounts are created by an administrator.</p>
        {formError && <div className="alert alert-error" role="alert">{formError}</div>}
        <Field label="Username" htmlFor="username" error={errors.username}>
          <input id="username" autoComplete="username" value={form.username} onChange={set('username')} autoFocus />
        </Field>
        <Field label="Email (optional)" htmlFor="email" error={errors.email}>
          <input id="email" type="email" autoComplete="email" value={form.email} onChange={set('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password} hint="At least 8 characters.">
          <input id="password" type="password" autoComplete="new-password" value={form.password} onChange={set('password')} />
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
        <p className="muted center">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
