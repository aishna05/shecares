import { useLocation } from "react-router-dom";

export function PageHead({ kicker, title, lede }) {
  return (
    <header className="page-head">
      {kicker && <p className="kicker">{kicker}</p>}
      <h1>{title}</h1>
      {lede && <p className="lede">{lede}</p>}
    </header>
  );
}

export function ErrorNote({ children }) {
  if (!children) return null;
  return (
    <p className="banner bad" role="alert">
      {children}
    </p>
  );
}

export function Flash() {
  const location = useLocation();
  if (!location.state?.flash) return null;
  return (
    <p className="banner good" role="status">
      {location.state.flash}
    </p>
  );
}

export function Empty({ children }) {
  return <p className="empty">{children}</p>;
}

export function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
