import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadReport } from "../api";
import { useAuth } from "../auth";
import { prettyDate, prettyTime, whenLabel } from "../format";
import { Empty, ErrorNote, Field, Flash, PageHead } from "../ui";

export function DoctorHome() {
  const { user, setUser } = useAuth();
  const [rows, setRows] = useState([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/auth/me/").then(setUser).catch(() => {});
    if (!user.is_approved) return;
    api("/appointments/")
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setReady(true));
  }, [user.is_approved]);

  if (!user.is_approved) {
    return (
      <PageHead
        kicker="Gynecologist"
        title={user.declined ? "This registration was not approved" : "Waiting for an admin to approve your account"}
        lede="Patients cannot see you, and you cannot open a chart, until the account is approved. The forum and articles are still open."
      />
    );
  }

  const today = rows.filter((item) => item.slot.date === user.today && item.status !== "cancelled");
  const later = rows.filter((item) => item.slot.date > user.today && item.status === "confirmed");

  return (
    <div>
      <PageHead kicker="Today" title={`Dr. ${user.first_name} ${user.last_name}`} lede="Urgent visits are listed first. Opening one tells the admin desk you have picked it up." />
      <Flash />
      <ErrorNote>{error}</ErrorNote>
      <h2>Today’s appointments</h2>
      {!ready && <p className="muted">Loading today’s list…</p>}
      {ready && today.length === 0 && <Empty>No one is booked for today. Add slots if the week looks empty.</Empty>}
      {today.map((item) => (
        <VisitCard key={item.id} item={item} />
      ))}
      <h2>Later</h2>
      {later.length === 0 && <Empty>No later visits.</Empty>}
      {later.map((item) => (
        <VisitCard key={item.id} item={item} />
      ))}
    </div>
  );
}

function VisitCard({ item }) {
  return (
    <article className={item.is_urgent && item.status === "confirmed" ? "card urgent-card" : "card"}>
      <p className="kicker">
        {prettyTime(item.slot.start_time)} · {item.status}
        {item.is_urgent ? " · urgent" : ""}
        {item.is_urgent && !item.acknowledged_at ? " · not picked up" : ""}
      </p>
      <h3>{item.patient.name}</h3>
      {item.symptoms && <p>{item.symptoms}</p>}
      <Link className="btn small" to={`/doctor/visits/${item.id}`}>Open visit</Link>
    </article>
  );
}

export function Schedule() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [slot, setSlot] = useState({ date: "", start: "10:00", end: "12:00", minutes: 20 });

  function load() {
    api("/doctors/me/").then(setProfile).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function saveProfile(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    const body = Object.fromEntries(form.entries());
    try {
      setProfile(await api("/doctors/me/", { method: "PUT", body }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function addSlots(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/doctors/me/slots/", { method: "POST", body: { ...slot, minutes: Number(slot.minutes) } });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeSlot(id) {
    try {
      await api(`/slots/${id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!profile) return <ErrorNote>{error || "Loading your schedule…"}</ErrorNote>;

  return (
    <div>
      <PageHead kicker="Schedule" title="Profile and free slots" lede="Patients only see open times. A booked slot stays until the visit is cancelled." />
      <ErrorNote>{error}</ErrorNote>
      {!user.is_approved && <p className="banner warn">Approval is still pending, so these slots are not visible to patients yet.</p>}
      <form className="card form" onSubmit={saveProfile}>
        <div className="grid-2">
          <Field label="First name"><input name="first_name" defaultValue={user.first_name} /></Field>
          <Field label="Last name"><input name="last_name" defaultValue={user.last_name} /></Field>
        </div>
        <Field label="Specialty"><input name="specialty" defaultValue={profile.specialty} /></Field>
        <Field label="Qualifications"><input name="qualifications" defaultValue={profile.qualifications} /></Field>
        <Field label="Clinic"><input name="clinic_name" defaultValue={profile.clinic_name} /></Field>
        <Field label="Address"><input name="clinic_address" defaultValue={profile.clinic_address} /></Field>
        <Field label="What you treat"><input name="treats" defaultValue={profile.treats.join(", ")} /></Field>
        <div className="grid-2">
          <Field label="Fee (₹)"><input name="fee" type="number" defaultValue={profile.fee} /></Field>
          <Field label="Years"><input name="experience_years" type="number" defaultValue={profile.experience_years} /></Field>
        </div>
        <Field label="Bio"><textarea name="bio" rows={3} defaultValue={profile.bio} /></Field>
        <button className="btn" type="submit">Save profile</button>
      </form>
      {user.is_approved && (
        <form className="card form" onSubmit={addSlots}>
          <h2>Add slots</h2>
          <div className="filters">
            <input type="date" required value={slot.date} onChange={(event) => setSlot({ ...slot, date: event.target.value })} />
            <input type="time" value={slot.start} onChange={(event) => setSlot({ ...slot, start: event.target.value })} />
            <input type="time" value={slot.end} onChange={(event) => setSlot({ ...slot, end: event.target.value })} />
            <input type="number" min="10" max="180" value={slot.minutes} onChange={(event) => setSlot({ ...slot, minutes: event.target.value })} />
            <button className="btn" type="submit">Add</button>
          </div>
          <p className="muted">Example: 10:00 to 12:00 every 20 minutes makes six visits.</p>
        </form>
      )}
      <div className="stack">
        {profile.slots.map((item) => (
          <article className="mini" key={item.id}>
            <div>
              <strong>{prettyDate(item.date)} · {prettyTime(item.start_time)}–{prettyTime(item.end_time)}</strong>
              <p className="muted">{item.is_booked ? `Booked${item.booked_by ? ` · ${item.booked_by}` : ""}` : "Open"}</p>
            </div>
            {!item.is_booked && <button className="btn small secondary" type="button" onClick={() => removeSlot(item.id)}>Remove</button>}
          </article>
        ))}
      </div>
    </div>
  );
}

export function Visit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [visit, setVisit] = useState(null);
  const [form, setForm] = useState({ medicines: "", advice: "", clinical_notes: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/appointments/${id}/acknowledge/`, { method: "POST" })
      .then((data) => {
        setVisit(data);
        if (data.prescription) {
          setForm({
            medicines: data.prescription.medicines,
            advice: data.prescription.advice,
            clinical_notes: data.clinical_notes || "",
          });
        }
      })
      .catch((err) => setError(err.message));
  }, [id]);

  async function complete(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/appointments/${id}/complete/`, { method: "POST", body: form });
      navigate("/doctor", { state: { flash: "Prescription saved on her record." } });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!visit) return <ErrorNote>{error || "Opening the visit…"}</ErrorNote>;
  const record = visit.record || { reports: [], periods: [], prescriptions: [], pregnancy: null };

  return (
    <div>
      <PageHead
        kicker={visit.is_urgent ? "Urgent visit" : "Clinic visit"}
        title={visit.patient.name}
        lede={`${whenLabel(visit.slot)} · ${visit.status}`}
      />
      <ErrorNote>{error}</ErrorNote>
      {visit.symptoms && <p className="card">{visit.symptoms}</p>}
      <div className="grid-2 align-start">
        <section>
          <h2>Her record</h2>
          <p className="muted">You can see this because she has a visit with you. Another doctor cannot.</p>
          <h3>Reports</h3>
          {record.reports.length === 0 && <Empty>No files uploaded.</Empty>}
          {record.reports.map((report) => (
            <article className="mini" key={report.id}>
              <span>{report.title}</span>
              <button className="btn small secondary" type="button" onClick={() => downloadReport(report.id, report.original_name).catch((err) => setError(err.message))}>
                Download
              </button>
            </article>
          ))}
          <h3>Periods</h3>
          {record.periods.length === 0 && <Empty>No cycle dates.</Empty>}
          {record.periods.map((item) => (
            <p key={item.id}>{prettyDate(item.start_date)} · {item.flow}{item.symptoms ? ` · ${item.symptoms}` : ""}</p>
          ))}
          <h3>Pregnancy log</h3>
          {record.pregnancy ? (
            <p>Week {record.pregnancy.weeks}. Due estimate {prettyDate(record.pregnancy.due_date)}. {record.pregnancy.note}</p>
          ) : (
            <Empty>No active pregnancy log.</Empty>
          )}
          <h3>Older prescriptions</h3>
          {record.prescriptions.length === 0 && <Empty>None on the account yet.</Empty>}
          {record.prescriptions.map((item) => (
            <article className="card" key={item.id}>
              <p className="kicker">Dr. {item.doctor_name}</p>
              <p className="pre">{item.medicines}</p>
            </article>
          ))}
        </section>
        <form className="card form" onSubmit={complete}>
          <h2>Write the prescription</h2>
          <Field label="Medicines">
            <textarea rows={6} required value={form.medicines} onChange={(event) => setForm({ ...form, medicines: event.target.value })} />
          </Field>
          <Field label="Advice">
            <textarea rows={3} value={form.advice} onChange={(event) => setForm({ ...form, advice: event.target.value })} />
          </Field>
          <Field label="Notes on her record">
            <textarea rows={4} value={form.clinical_notes} onChange={(event) => setForm({ ...form, clinical_notes: event.target.value })} />
          </Field>
          <button className="btn" type="submit" disabled={busy || visit.status === "cancelled"}>
            {visit.status === "completed" ? "Update prescription" : "Save prescription and complete visit"}
          </button>
        </form>
      </div>
    </div>
  );
}

export function WriteArticle() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", summary: "", body: "" });
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    try {
      const article = await api("/articles/", { method: "POST", body: { ...form, is_published: true } });
      navigate(`/articles/${article.id}`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="card form narrow-form" onSubmit={submit}>
      <PageHead kicker="Article" title="Write for patients" lede="Only an approved doctor account can publish. Say what the piece is, and say it is not a diagnosis." />
      <ErrorNote>{error}</ErrorNote>
      <Field label="Title"><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></Field>
      <Field label="Summary"><input value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} required /></Field>
      <Field label="Article"><textarea rows={10} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} required /></Field>
      <button className="btn" type="submit">Publish</button>
    </form>
  );
}
