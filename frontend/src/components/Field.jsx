/** A labelled form control with an inline error message. */
export default function Field({ label, error, hint, children, htmlFor }) {
  return (
    <div className={`field ${error ? 'field-error' : ''}`}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && !error && <small className="hint">{hint}</small>}
      {error && <small className="error-text" role="alert">{error}</small>}
    </div>
  );
}
