import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, downloadReport } from "../api";
import { useAuth } from "../auth";
import { prettyDate, prettyTime, ratingLabel, whenLabel } from "../format";
import { Empty, ErrorNote, Field, Flash, PageHead } from "../ui";

export function PatientHome() {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [notes, setNotes] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api("/appointments/"), api("/reminders/")])
      .then(([visits, reminders]) => {
        setAppointments(visits);
        setNotes(reminders.filter((item) => !item.is_read));
      })
      .catch((err) => setError(err.message));
  }, []);

  const upcoming = appointments.filter((item) => item.status === "confirmed" && item.slot.date >= user.today);
  const prescriptions = appointments.filter((item) => item.prescription);

  return (
    <div>
      <PageHead kicker="Patient" title={`Hello, ${user.first_name}`} lede="Book a clinic visit, keep reports in this login, and log a period or a pregnancy." />
      <ErrorNote>{error}</ErrorNote>
      <div className="row">
        <Link className="btn" to="/patient/doctors">Find a doctor</Link>
        <Link className="btn secondary" to="/patient/records">Open my folder</Link>
        <Link className="btn secondary" to="/patient/tracker">Update cycle log</Link>
      </div>
      <div className="grid-2">
        <section>
          <h2>Reminders</h2>
          {notes.length === 0 && <Empty>Nothing waiting. A reminder appears after you log a cycle or book a visit.</Empty>}
          {notes.map((note) => (
            <article className="card" key={note.id}><p>{note.message}</p></article>
          ))}
        </section>
        <section>
          <h2>Upcoming visits</h2>
          {upcoming.length === 0 && <Empty>No clinic visit booked.</Empty>}
          {upcoming.map((item) => (
            <article className="card" key={item.id}>
              <p className="kicker">{whenLabel(item.slot)}{item.is_urgent ? " · urgent" : ""}</p>
              <h3>Dr. {item.doctor.name}</h3>
              <p>{item.doctor.specialty} · {item.doctor.clinic_name}</p>
            </article>
          ))}
        </section>
      </div>
      <section>
        <h2>Prescriptions already on this account</h2>
        {prescriptions.length === 0 && <Empty>None yet. They show up here after the doctor writes one.</Empty>}
        {prescriptions.map((item) => (
          <article className="card" key={item.id}>
            <p className="kicker">Dr. {item.prescription.doctor_name} · {prettyDate(item.slot.date)}</p>
            <p className="pre">{item.prescription.medicines}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function DoctorCard({ doctor, symptoms }) {
  const query = symptoms ? `?symptoms=${encodeURIComponent(symptoms)}` : "";
  return (
    <article className="card doctor-card">
      <div>
        <p className="kicker">{doctor.specialty}</p>
        <h3>Dr. {doctor.name}</h3>
        <p>{doctor.qualifications} · {doctor.experience_years} years</p>
        <p>{doctor.clinic_name}</p>
        <p className="muted">{doctor.clinic_address}</p>
        <p className="stars">{ratingLabel(doctor.rating_avg, doctor.rating_count)}</p>
        {doctor.reasons?.length > 0 && <p className="badge leaf">Matched: {doctor.reasons.join(", ")}</p>}
      </div>
      <div>
        <p className="fee">₹{doctor.fee}</p>
        <p>{doctor.open_slots} open slots</p>
        <p className="muted">Next: {whenLabel(doctor.next_slot)}</p>
        <Link className="btn small" to={`/patient/doctors/${doctor.id}${query}`}>View slots</Link>
      </div>
    </article>
  );
}

export function FindDoctor() {
  const [specialties, setSpecialties] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [filters, setFilters] = useState({ q: "", specialty: "", min_rating: "", date: "" });
  const [symptoms, setSymptoms] = useState("");
  const [notice, setNotice] = useState(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  function load(next = filters) {
    const params = new URLSearchParams();
    Object.entries(next).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    return api(`/doctors/?${params.toString()}`)
      .then((data) => {
        setSpecialties(data.specialties);
        setDoctors(data.doctors);
        setNotice(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setReady(true));
  }

  useEffect(() => {
    load();
  }, []);

  async function search(event) {
    event.preventDefault();
    setError("");
    await load(filters);
  }

  async function suggest(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/doctors/suggest/", { method: "POST", body: { symptoms } });
      setDoctors(data.doctors);
      setNotice(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Find a doctor" title="Search, or describe what you are feeling" lede="Symptoms are optional. They only match words to a gynecologist's listed specialty. SheCares does not diagnose illness." />
      <ErrorNote>{error}</ErrorNote>
      <form className="card form" onSubmit={suggest}>
        <Field label="What are you feeling? (optional)">
          <textarea rows={3} value={symptoms} onChange={(event) => setSymptoms(event.target.value)} placeholder="Example: irregular periods and cramps" />
        </Field>
        <button className="btn" type="submit">Suggest a doctor</button>
      </form>
      {notice && (
        <div className="banner warn">
          <p>{notice.disclaimer}</p>
          {notice.message && <p>{notice.message}</p>}
        </div>
      )}
      <form className="filters" onSubmit={search}>
        <input placeholder="Name, clinic, or concern" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
        <select value={filters.specialty} onChange={(event) => setFilters({ ...filters, specialty: event.target.value })}>
          <option value="">Any specialty</option>
          {specialties.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={filters.min_rating} onChange={(event) => setFilters({ ...filters, min_rating: event.target.value })}>
          <option value="">Any rating</option>
          <option value="4">4 and up</option>
          <option value="3">3 and up</option>
        </select>
        <input type="date" value={filters.date} onChange={(event) => setFilters({ ...filters, date: event.target.value })} />
        <button className="btn secondary" type="submit">Search</button>
      </form>
      <div className="stack">
        {!ready && <p className="muted">Loading gynecologists…</p>}
        {ready && doctors.length === 0 && <Empty>No gynecologist matched that search.</Empty>}
        {doctors.map((doctor) => <DoctorCard key={doctor.id} doctor={doctor} symptoms={symptoms} />)}
      </div>
    </div>
  );
}

export function DoctorDetail() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [doctor, setDoctor] = useState(null);
  const [selected, setSelected] = useState(null);
  const [symptoms, setSymptoms] = useState(params.get("symptoms") || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/doctors/${id}/`).then(setDoctor).catch((err) => setError(err.message));
  }, [id]);

  async function book(urgent) {
    if (!selected) {
      setError("Choose a slot first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/appointments/", { method: "POST", body: { slot_id: selected, symptoms, is_urgent: urgent } });
      navigate("/patient/appointments", {
        state: { flash: urgent ? "Urgent visit booked. It goes to the front of that doctor's list." : "Clinic visit booked." },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!doctor) return error ? <ErrorNote>{error}</ErrorNote> : <p className="muted">Loading the doctor…</p>;
  const groups = doctor.slots.reduce((map, slot) => {
    map[slot.date] = map[slot.date] || [];
    map[slot.date].push(slot);
    return map;
  }, {});

  return (
    <div className="grid-2 align-start">
      <section>
        <PageHead kicker={doctor.specialty} title={`Dr. ${doctor.name}`} lede={doctor.bio} />
        <p>{doctor.qualifications} · {doctor.experience_years} years · ₹{doctor.fee}</p>
        <p>{doctor.clinic_name}<br />{doctor.clinic_address}</p>
        <p className="stars">{ratingLabel(doctor.rating_avg, doctor.rating_count)}</p>
        <p>Treats: {doctor.treats.join(", ") || doctor.specialty}</p>
        <h2>Open slots</h2>
        {doctor.slots.length === 0 && <Empty>No open clinic slots right now.</Empty>}
        {Object.entries(groups).map(([date, slots]) => (
          <div key={date}>
            <p className="kicker">{prettyDate(date)}</p>
            <div className="slots">
              {slots.map((slot) => (
                <button key={slot.id} type="button" className={selected === slot.id ? "slot selected" : "slot"} onClick={() => setSelected(slot.id)}>
                  {prettyTime(slot.start_time)}
                </button>
              ))}
            </div>
          </div>
        ))}
      </section>
      <aside className="card form">
        <h2>Book the clinic visit</h2>
        <ErrorNote>{error}</ErrorNote>
        <Field label="Anything you want this doctor to read beforehand">
          <textarea rows={4} value={symptoms} onChange={(event) => setSymptoms(event.target.value)} />
        </Field>
        <p className="muted">This note is stored on the booking. It is not a diagnosis.</p>
        <button className="btn" type="button" disabled={busy} onClick={() => book(false)}>Book this visit</button>
        <button className="btn urgent" type="button" disabled={busy} onClick={() => book(true)}>Mark this visit as urgent</button>
      </aside>
    </div>
  );
}

export function Appointments() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [scores, setScores] = useState({});

  function load() {
    api("/appointments/").then(setRows).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function cancel(id) {
    if (!window.confirm("Cancel this clinic visit?")) return;
    try {
      await api(`/appointments/${id}/cancel/`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function rate(id) {
    try {
      await api(`/appointments/${id}/rate/`, { method: "POST", body: scores[id] || { score: 5, comment: "" } });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const upcoming = rows.filter((item) => item.status === "confirmed");
  const past = rows.filter((item) => item.status !== "confirmed");

  return (
    <div>
      <PageHead kicker="Visits" title="Upcoming visits and old prescriptions" />
      <Flash />
      <ErrorNote>{error}</ErrorNote>
      <h2>Upcoming</h2>
      {upcoming.length === 0 && <Empty>Nothing booked. The calendar starts when you pick a slot.</Empty>}
      {upcoming.map((item) => (
        <article className="card" key={item.id}>
          <p className="kicker">{whenLabel(item.slot)} · {item.status}{item.is_urgent ? " · urgent" : ""}</p>
          <h3>Dr. {item.doctor.name}</h3>
          <p>{item.doctor.clinic_name}</p>
          {item.symptoms && <p>{item.symptoms}</p>}
          <button className="btn small secondary" type="button" onClick={() => cancel(item.id)}>Cancel visit</button>
        </article>
      ))}
      <h2>Past</h2>
      {past.length === 0 && <Empty>No past visits yet.</Empty>}
      {past.map((item) => (
        <article className="card" key={item.id}>
          <p className="kicker">{prettyDate(item.slot.date)} · {item.status}</p>
          <h3>Dr. {item.doctor.name}</h3>
          {item.prescription ? (
            <>
              <p className="pre">{item.prescription.medicines}</p>
              {item.prescription.advice && <p>{item.prescription.advice}</p>}
            </>
          ) : (
            <p className="muted">No prescription on this visit.</p>
          )}
          {item.clinical_notes && <p className="muted">Note from the doctor: {item.clinical_notes}</p>}
          {item.status === "completed" && !item.rating && (
            <div className="row">
              <select
                value={scores[item.id]?.score || 5}
                onChange={(event) => setScores({ ...scores, [item.id]: { ...(scores[item.id] || {}), score: Number(event.target.value) } })}
              >
                {[5, 4, 3, 2, 1].map((score) => <option key={score} value={score}>{score} stars</option>)}
              </select>
              <input
                placeholder="Short comment"
                value={scores[item.id]?.comment || ""}
                onChange={(event) => setScores({ ...scores, [item.id]: { score: scores[item.id]?.score || 5, comment: event.target.value } })}
              />
              <button className="btn small" type="button" onClick={() => rate(item.id)}>Save rating</button>
            </div>
          )}
          {item.rating && <p className="stars">{item.rating.score} / 5 · {item.rating.comment}</p>}
        </article>
      ))}
      <p className="muted">Today on the server is {prettyDate(user.today)}.</p>
    </div>
  );
}

export function Records() {
  const [reports, setReports] = useState([]);
  const [visits, setVisits] = useState([]);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  function load() {
    Promise.all([api("/reports/"), api("/appointments/")])
      .then(([files, appointments]) => {
        setReports(files);
        setVisits(appointments);
      })
      .catch((err) => setError(err.message))
      .finally(() => setReady(true));
  }

  useEffect(() => {
    load();
  }, []);

  async function upload(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a PDF or an image.");
      return;
    }
    const body = new FormData();
    body.append("title", title);
    body.append("file", file);
    setError("");
    try {
      await api("/reports/", { method: "POST", body });
      setTitle("");
      setFile(null);
      event.target.reset();
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const prescriptions = visits.filter((item) => item.prescription);

  return (
    <div>
      <PageHead kicker="Records" title="Prescriptions and reports, one folder" lede="Files are stored encrypted. Only you, and a doctor you have a visit with, can open them." />
      <ErrorNote>{error}</ErrorNote>
      <form className="card form" onSubmit={upload}>
        <Field label="Report title"><input value={title} onChange={(event) => setTitle(event.target.value)} required /></Field>
        <Field label="PDF or image"><input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*" onChange={(event) => setFile(event.target.files[0])} /></Field>
        <button className="btn" type="submit">Add to my folder</button>
      </form>
      <h2>Reports</h2>
      {!ready && <p className="muted">Loading the folder…</p>}
      {ready && reports.length === 0 && <Empty>The folder is empty.</Empty>}
      {reports.map((report) => (
        <article className="card row spread" key={report.id}>
          <div>
            <h3>{report.title}</h3>
            <p className="muted">{report.original_name}</p>
          </div>
          <button className="btn small secondary" type="button" onClick={() => downloadReport(report.id, report.original_name).catch((err) => setError(err.message))}>
            Download
          </button>
        </article>
      ))}
      <h2>Prescriptions</h2>
      {prescriptions.map((item) => (
        <article className="card" key={item.id}>
          <p className="kicker">{prettyDate(item.slot.date)} · Dr. {item.prescription.doctor_name}</p>
          <p className="pre">{item.prescription.medicines}</p>
          {item.prescription.advice && <p>{item.prescription.advice}</p>}
        </article>
      ))}
    </div>
  );
}

export function Tracker() {
  const { user, setUser } = useAuth();
  const location = useLocation();
  const [periods, setPeriods] = useState([]);
  const [pregnancy, setPregnancy] = useState(null);
  const [cycle, setCycle] = useState(user.cycle_length || 28);
  const [period, setPeriod] = useState({ start_date: "", end_date: "", flow: "medium", symptoms: "", notes: "" });
  const [preg, setPreg] = useState({ lmp: "", notes: "" });
  const [error, setError] = useState("");

  function load() {
    Promise.all([api("/periods/"), api("/pregnancy/")])
      .then(([logs, current]) => {
        setPeriods(logs);
        setPregnancy(current.active);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, [location.pathname]);

  async function saveCycle(event) {
    event.preventDefault();
    try {
      setUser(await api("/auth/me/", { method: "PATCH", body: { cycle_length: Number(cycle) } }));
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function savePeriod(event) {
    event.preventDefault();
    try {
      await api("/periods/", { method: "POST", body: period });
      setPeriod({ start_date: "", end_date: "", flow: "medium", symptoms: "", notes: "" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removePeriod(id) {
    await api(`/periods/${id}/`, { method: "DELETE" });
    load();
  }

  async function savePregnancy(event) {
    event.preventDefault();
    try {
      const data = await api("/pregnancy/", { method: "POST", body: preg });
      setPregnancy(data.active);
    } catch (err) {
      setError(err.message);
    }
  }

  async function closePregnancy() {
    const data = await api("/pregnancy/close/", { method: "POST" });
    setPregnancy(data.active);
  }

  return (
    <div>
      <PageHead kicker="Cycle" title="Period and pregnancy log" lede="Reminders use the dates you type. They are not a prediction from a doctor, and logging a pregnancy here does not confirm one." />
      <ErrorNote>{error}</ErrorNote>
      <div className="grid-2 align-start">
        <section className="card form">
          <h2>Period</h2>
          <form onSubmit={saveCycle} className="row">
            <Field label="Usual cycle length (days)">
              <input type="number" min="15" max="60" value={cycle} onChange={(event) => setCycle(event.target.value)} />
            </Field>
            <button className="btn small secondary" type="submit">Save</button>
          </form>
          <form onSubmit={savePeriod}>
            <Field label="Start date"><input type="date" required value={period.start_date} onChange={(event) => setPeriod({ ...period, start_date: event.target.value })} /></Field>
            <Field label="End date"><input type="date" value={period.end_date} onChange={(event) => setPeriod({ ...period, end_date: event.target.value })} /></Field>
            <Field label="Flow">
              <select value={period.flow} onChange={(event) => setPeriod({ ...period, flow: event.target.value })}>
                <option value="light">Light</option>
                <option value="medium">Medium</option>
                <option value="heavy">Heavy</option>
              </select>
            </Field>
            <Field label="Symptoms"><input value={period.symptoms} onChange={(event) => setPeriod({ ...period, symptoms: event.target.value })} /></Field>
            <Field label="Notes"><textarea rows={2} value={period.notes} onChange={(event) => setPeriod({ ...period, notes: event.target.value })} /></Field>
            <button className="btn" type="submit">Save period</button>
          </form>
          <div className="stack">
            {periods.map((item) => (
              <article key={item.id} className="mini">
                <div>
                  <strong>{prettyDate(item.start_date)}</strong>
                  <p className="muted">{item.flow}{item.symptoms ? ` · ${item.symptoms}` : ""}</p>
                </div>
                <button className="btn small secondary" type="button" onClick={() => removePeriod(item.id)}>Remove</button>
              </article>
            ))}
          </div>
        </section>
        <section className="card form">
          <h2>Pregnancy</h2>
          {pregnancy && (
            <div className="banner warn">
              <p>About week {pregnancy.weeks}. Estimated due date {prettyDate(pregnancy.due_date)}.</p>
              <p>{pregnancy.note}</p>
            </div>
          )}
          <form onSubmit={savePregnancy}>
            <Field label="First day of your last period">
              <input type="date" required value={preg.lmp} onChange={(event) => setPreg({ ...preg, lmp: event.target.value })} />
            </Field>
            <Field label="Notes"><textarea rows={3} value={preg.notes} onChange={(event) => setPreg({ ...preg, notes: event.target.value })} /></Field>
            <button className="btn" type="submit">Save pregnancy dates</button>
          </form>
          {pregnancy && <button className="btn secondary" type="button" onClick={closePregnancy}>Close this pregnancy log</button>}
        </section>
      </div>
    </div>
  );
}
