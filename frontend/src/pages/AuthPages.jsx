import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { homeFor } from "../format";
import { ErrorNote, Field, PageHead } from "../ui";

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={homeFor(user)} replace />;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const next = await login(email, password);
      navigate(homeFor(next));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form narrow-form" onSubmit={submit}>
      <PageHead kicker="Log in" title="Log in" lede="Patients, gynecologists, and admins each land on their own screen." />
      <ErrorNote>{error}</ErrorNote>
      <Field label="Email">
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required autoComplete="username" />
      </Field>
      <Field label="Password">
        <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required autoComplete="current-password" />
      </Field>
      <button className="btn" type="submit" disabled={busy}>
        {busy ? "Checking…" : "Log in"}
      </button>
      <p className="muted">
        New here? <Link to="/register">Create an account</Link>
      </p>
    </form>
  );
}

export function Register() {
  const { user, acceptSession } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState("patient");
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    phone: "",
    city: "",
    specialty: "General gynecology",
    qualifications: "",
    clinic_name: "",
    clinic_address: "",
    fee: "",
    experience_years: "",
    treats: "",
    bio: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={homeFor(user)} replace />;

  function set(field) {
    return (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/register/", { method: "POST", body: { ...form, role, fee: Number(form.fee || 0), experience_years: Number(form.experience_years || 0) } });
      acceptSession(data);
      navigate(homeFor(data.user));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form narrow-form" onSubmit={submit}>
      <PageHead kicker="Register" title="Create a login" lede="Patients can book immediately. Gynecologists wait until an admin approves the account. Admin accounts are not open for signup." />
      <ErrorNote>{error}</ErrorNote>
      <div className="role-switch">
        <button type="button" className={role === "patient" ? "on" : ""} onClick={() => setRole("patient")}>
          Patient
        </button>
        <button type="button" className={role === "doctor" ? "on" : ""} onClick={() => setRole("doctor")}>
          Gynecologist
        </button>
      </div>
      <div className="grid-2">
        <Field label="First name">
          <input value={form.first_name} onChange={set("first_name")} required />
        </Field>
        <Field label="Last name">
          <input value={form.last_name} onChange={set("last_name")} />
        </Field>
      </div>
      <Field label="Email">
        <input type="email" value={form.email} onChange={set("email")} required />
      </Field>
      <Field label="Password">
        <input type="password" value={form.password} onChange={set("password")} required minLength={8} />
      </Field>
      <Field label="Phone">
        <input value={form.phone} onChange={set("phone")} />
      </Field>
      {role === "patient" ? (
        <Field label="City">
          <input value={form.city} onChange={set("city")} />
        </Field>
      ) : (
        <>
          <Field label="Specialty">
            <select value={form.specialty} onChange={set("specialty")}>
              {["General gynecology", "Obstetrics", "Fertility", "Menstrual health", "Menopause"].map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="Qualifications">
            <input value={form.qualifications} onChange={set("qualifications")} required />
          </Field>
          <Field label="Clinic name">
            <input value={form.clinic_name} onChange={set("clinic_name")} required />
          </Field>
          <Field label="Clinic address">
            <input value={form.clinic_address} onChange={set("clinic_address")} />
          </Field>
          <div className="grid-2">
            <Field label="Fee (₹)">
              <input type="number" min="0" value={form.fee} onChange={set("fee")} />
            </Field>
            <Field label="Years of experience">
              <input type="number" min="0" value={form.experience_years} onChange={set("experience_years")} />
            </Field>
          </div>
          <Field label="What you treat">
            <input value={form.treats} onChange={set("treats")} placeholder="period, pregnancy, checkup" />
          </Field>
          <Field label="Short bio">
            <textarea value={form.bio} onChange={set("bio")} rows={3} />
          </Field>
        </>
      )}
      <button className="btn" type="submit" disabled={busy}>
        {busy ? "Creating…" : "Create account"}
      </button>
      <p className="muted">
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </form>
  );
}
