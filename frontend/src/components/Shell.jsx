import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { homeFor } from "../format";

const LINKS = {
  patient: [
    ["/patient", "Home"],
    ["/patient/doctors", "Find a doctor"],
    ["/patient/appointments", "Visits"],
    ["/patient/records", "Records"],
    ["/patient/tracker", "Cycle"],
    ["/forum", "Forum"],
    ["/articles", "Articles"],
  ],
  doctor: [
    ["/doctor", "Today"],
    ["/doctor/schedule", "Schedule"],
    ["/forum", "Forum"],
    ["/articles", "Articles"],
    ["/doctor/articles/new", "Write"],
  ],
  admin: [
    ["/admin", "Overview"],
    ["/admin/doctors", "Doctors"],
    ["/admin/forum", "Forum"],
    ["/admin/urgent", "Urgent"],
    ["/admin/complaints", "Complaints"],
    ["/admin/logs", "Logs"],
  ],
};

export default function Shell() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState([]);

  useEffect(() => {
    if (!user) {
      setNotes([]);
      return;
    }
    api("/reminders/")
      .then(setNotes)
      .catch(() => setNotes([]));
  }, [user, location.pathname]);

  const links = user ? linksFor(user) : [];
  const unread = notes.filter((note) => !note.is_read);

  async function markRead(id) {
    const updated = await api(`/reminders/${id}/read/`, { method: "POST" });
    setNotes((current) => current.map((note) => (note.id === id ? updated : note)));
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link to={user ? homeFor(user) : "/"} className="brand">
          <span className="mark" aria-hidden="true" />
          SheCares
        </Link>
        <nav className="nav">
          {!user && (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/register" className="nav-cta">
                Create account
              </NavLink>
            </>
          )}
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/patient" || to === "/doctor" || to === "/admin" || to === "/forum" || to === "/articles"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="top-actions">
          {user && (
            <div className="bell-wrap">
              <button className="bell" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
                Reminders
                {unread.length > 0 && <span className="count">{unread.length}</span>}
              </button>
              {open && (
                <div className="menu">
                  {notes.length === 0 && <p className="muted">No reminders yet.</p>}
                  {notes.slice(0, 6).map((note) => (
                    <button key={note.id} type="button" className={note.is_read ? "note read" : "note"} onClick={() => markRead(note.id)}>
                      <strong>{note.kind}</strong>
                      <span>{note.message}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {user && (
            <button
              className="btn small secondary"
              type="button"
              onClick={() => {
                logout();
                navigate("/");
              }}
            >
              Log out
            </button>
          )}
        </div>
      </header>
      <p className="disclaimer">
        SheCares does not diagnose illness and is not an emergency ward. If you are in real trouble, go to a hospital.
      </p>
      <main className="main">{loading ? <p className="muted">Loading…</p> : <Outlet />}</main>
      <footer className="footer">
        <div>
          <strong>SheCares</strong>
          <p>One login for a gynecologist, your reports, and a cycle or pregnancy log.</p>
        </div>
        <div className="footer-links">
          {user && <Link to="/complaints">Raise a complaint</Link>}
          <a href="https://github.com/SheCares-SE/SheCares">Project repo</a>
        </div>
      </footer>
    </div>
  );
}

function linksFor(user) {
  if (user.role === "doctor" && !user.is_approved) {
    return [
      ["/doctor", "Today"],
      ["/forum", "Forum"],
      ["/articles", "Articles"],
    ];
  }
  return LINKS[user.role] || [];
}
