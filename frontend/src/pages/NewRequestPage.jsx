import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRequest } from '../api/endpoints';
import Field from '../components/Field';
import { CATEGORIES, PRIORITIES } from '../constants';
import { useRequests } from '../context/RequestsContext';
import { useToast } from '../context/ToastContext';
import { validateRequestForm } from '../utils/validation';

export default function NewRequestPage() {
  const navigate = useNavigate();
  const { dispatch } = useRequests();
  const toast = useToast();
  const [form, setForm] = useState({ title: '', description: '', category: '', priority: 'NORMAL' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (errors[key]) setErrors((er) => ({ ...er, [key]: undefined })); // clear as the user fixes it
  };

  async function onSubmit(e) {
    e.preventDefault();
    const clientErrors = validateRequestForm(form);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    setBusy(true);
    setFormError('');
    try {
      const created = await createRequest({
        title: form.title.trim(),
        description: form.description.trim(),
        category: form.category,
        priority: form.priority,
      });
      dispatch({ type: 'upsert_many', requests: [created] });
      toast.push(`Request #${created.id} submitted. Processing will start shortly.`, 'success');
      navigate(`/requests/${created.id}`);
    } catch (err) {
      if (err.status === 400 && err.details) {
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
    <>
      <div className="page-head">
        <div>
          <h1>New service request</h1>
          <p className="muted">A supervisor is assigned automatically, and processing starts in the background.</p>
        </div>
      </div>
      <form className="card form-card" onSubmit={onSubmit} noValidate>
        {formError && <div className="alert alert-error" role="alert">{formError}</div>}
        <Field label="Title" htmlFor="title" error={errors.title} hint="A short summary, e.g. 'AC not cooling'.">
          <input id="title" value={form.title} onChange={set('title')} maxLength={200} autoFocus />
        </Field>
        <Field label="Description" htmlFor="description" error={errors.description}>
          <textarea id="description" rows={5} value={form.description} onChange={set('description')} maxLength={5000} />
        </Field>
        <div className="row">
          <Field label="Category" htmlFor="category" error={errors.category}>
            <select id="category" value={form.category} onChange={set('category')}>
              <option value="">Select…</option>
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>
          <Field label="Priority" htmlFor="priority" error={errors.priority}>
            <select id="priority" value={form.priority} onChange={set('priority')}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </Field>
        </div>
        <div className="actions">
          <button type="button" className="btn" onClick={() => navigate('/')}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit request'}</button>
        </div>
      </form>
    </>
  );
}
