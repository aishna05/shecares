import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { prettyDate, prettyTime, waitLabel, whenLabel } from "../format";
import { Empty, ErrorNote, PageHead } from "../ui";

export function AdminHome() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/admin/summary/").then(setSummary).catch((err) => setError(err.message));
  }, []);

  if (!summary) return <ErrorNote>{error || "Loading the desk…"}</ErrorNote>;

  return (
    <div>
      <PageHead
        kicker="Admin"
        title="Accounts, the forum, and delays"
        lede="This desk manages doctor accounts, the forum, complaints, and urgent-request delays. It does not open prescriptions, reports, or cycle notes."
      />
      <div className="stats">
        <article><strong>{summary.pending_doctors}</strong><p>doctors waiting</p></article>
        <article><strong>{summary.urgent_waiting}</strong><p>urgent requests not picked up</p></article>
        <article><strong>{summary.open_complaints}</strong><p>open complaints</p></article>
        <article><strong>{summary.removed_posts}</strong><p>posts already removed</p></article>
      </div>
      <h2>Urgent requests still waiting</h2>
      {summary.urgent.length === 0 && <Empty>Nothing urgent is sitting unacknowledged.</Empty>}
      {summary.urgent.map((item) => (
        <article className="card" key={item.id}>
          <p className="kicker">{item.patient_name} · Dr. {item.doctor_name}</p>
          <p>{whenLabel(item.when)} · {waitLabel(item.waiting_minutes)}</p>
        </article>
      ))}
      <div className="row">
        <Link className="btn" to="/admin/doctors">Review doctors</Link>
        <Link className="btn secondary" to="/admin/forum">Moderate the forum</Link>
        <Link className="btn secondary" to="/articles">Put up an article</Link>
      </div>
    </div>
  );
}

export function AdminDoctors() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  function load() {
    api("/admin/doctors/").then(setRows).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function act(id, action) {
    try {
      await api(`/admin/doctors/${id}/${action}/`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Doctors" title="Approve who can see patients" lede="Approving an account lets her publish slots and articles. It does not show you her patients' files." />
      <ErrorNote>{error}</ErrorNote>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Specialty</th>
              <th>Clinic</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((doctor) => (
              <tr key={doctor.id}>
                <td>{doctor.name}<br /><span className="muted">{doctor.email}</span></td>
                <td>{doctor.specialty}<br /><span className="muted">{doctor.qualifications}</span></td>
                <td>{doctor.clinic_name}</td>
                <td>{doctor.is_approved ? "Approved" : doctor.declined ? "Declined" : "Waiting"}</td>
                <td className="row">
                  {!doctor.is_approved && <button className="btn small" type="button" onClick={() => act(doctor.id, "approve")}>Approve</button>}
                  {!doctor.declined && <button className="btn small secondary" type="button" onClick={() => act(doctor.id, "decline")}>Decline</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AdminForum() {
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");

  function load() {
    api("/forum/posts/?all=1").then(setPosts).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function moderate(id, action) {
    try {
      await api(`/forum/posts/${id}/moderate/`, { method: "POST", body: { action, reason: "Removed by admin" } });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Forum" title="Remove junk" lede="Health articles still have to come from a doctor account. This page only keeps the forum clean." />
      <ErrorNote>{error}</ErrorNote>
      <div className="stack">
        {posts.map((post) => (
          <article className={post.is_removed ? "card removed" : "card"} key={post.id}>
            <p className="kicker">{post.author.name} · {post.author.role}</p>
            <h2><Link to={`/forum/${post.id}`}>{post.title}</Link></h2>
            <p>{post.body}</p>
            {post.is_removed ? (
              <button className="btn small secondary" type="button" onClick={() => moderate(post.id, "restore")}>Restore</button>
            ) : (
              <button className="btn small" type="button" onClick={() => moderate(post.id, "remove")}>Remove post</button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

export function AdminUrgent() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/admin/urgent/").then(setRows).catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <PageHead kicker="Urgent" title="Who is still waiting" lede="You can see the wait. You cannot see the symptom note." />
      <ErrorNote>{error}</ErrorNote>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Slot</th>
              <th>Status</th>
              <th>Delay</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id} className={item.waiting_minutes > 60 ? "late" : ""}>
                <td>{item.patient_name}</td>
                <td>{item.doctor_name}</td>
                <td>{prettyDate(item.when.date)} {prettyTime(item.when.start_time)}</td>
                <td>{item.status}</td>
                <td>{waitLabel(item.waiting_minutes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <Empty>No urgent bookings.</Empty>}
    </div>
  );
}

export function AdminComplaints() {
  const [rows, setRows] = useState([]);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState("");

  function load() {
    api("/complaints/").then(setRows).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function resolve(id) {
    try {
      await api(`/complaints/${id}/resolve/`, { method: "POST", body: { admin_note: notes[id] || "" } });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Complaints" title="Handle what people reported" />
      <ErrorNote>{error}</ErrorNote>
      <div className="stack">
        {rows.map((row) => (
          <article className="card" key={row.id}>
            <p className="kicker">{row.user_name} · {row.user_role} · {row.status}</p>
            <h2>{row.subject}</h2>
            <p>{row.body}</p>
            {row.status === "open" ? (
              <div className="row">
                <input placeholder="Note back to them" value={notes[row.id] || ""} onChange={(event) => setNotes({ ...notes, [row.id]: event.target.value })} />
                <button className="btn small" type="button" onClick={() => resolve(row.id)}>Resolve</button>
              </div>
            ) : (
              <p className="muted">{row.admin_note}</p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

export function AdminLogs() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/admin/logs/").then(setRows).catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <PageHead kicker="Access" title="Login and access log" lede="The log records the action. It does not store symptoms, prescriptions, or file contents." />
      <ErrorNote>{error}</ErrorNote>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.created_at.replace("T", " ").slice(0, 16)}</td>
                <td>{row.user_name}<br /><span className="muted">{row.user_role}</span></td>
                <td>{row.action}</td>
                <td>{row.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
