import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { homeFor } from "../format";

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="story">
      <section className="hero">
        <div>
          <p className="kicker light">Women's health, in one login</p>
          <h1>SheCares</h1>
          <p className="lede light">
            A website where women can talk to a gynecologist, keep their reports, and track periods or pregnancy — without running around between apps.
          </p>
          <div className="row">
            <Link className="btn light" to={user ? homeFor(user) : "/register"}>
              {user ? "Go to your desk" : "Create an account"}
            </Link>
            <Link className="btn ghost" to="/login">
              Log in
            </Link>
          </div>
          <p className="tech">Built with React (Vite), Django, and SQL.</p>
        </div>
        <aside className="hero-card">
          <p className="kicker">Today</p>
          <h2>Clinic visit, 4:30 pm</h2>
          <p>Dr. Ananya Shah · Obstetrics</p>
          <p className="badge urgent">Urgent</p>
          <hr />
          <p className="kicker">Reminder</p>
          <p>Next period may start in 8 days. Dates stay on your account.</p>
        </aside>
      </section>

      <section>
        <p className="kicker">What it includes</p>
        <h2>The things that used to live in three different apps.</h2>
        <div className="grid-3">
          {[
            ["Search", "Doctors by specialty, timing, and ratings."],
            ["Book", "A clinic visit online, with the open slots visible."],
            ["Suggest", "A doctor from the symptoms she types in. Not a diagnosis."],
            ["Folder", "A digital prescription and a place for reports."],
            ["One list", "Upcoming visits and past prescriptions together."],
            ["Tracker", "Period and pregnancy log, with simple reminders."],
            ["Forum", "A watched forum, plus articles from doctors."],
            ["Urgent", "A button to mark the visit as urgent."],
            ["Three desks", "Patient, gynecologist, and admin. Same website."],
          ].map(([title, copy]) => (
            <article className="card" key={title}>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="split">
        <div>
          <p className="kicker">Who logs in</p>
          <h2>Same website, three different screens.</h2>
          <p>That is the point of role-based access. An admin checks accounts and the forum. An admin does not open medical files.</p>
        </div>
        <div className="stack">
          <article className="card">
            <h3>Patient</h3>
            <p>Books, uploads reports, tracks her cycle.</p>
          </article>
          <article className="card">
            <h3>Gynecologist</h3>
            <p>Sees her patients, writes prescriptions, keeps her own slots.</p>
          </article>
          <article className="card">
            <h3>Admin</h3>
            <p>Checks doctor accounts, keeps the forum clean, watches urgent-request delays.</p>
          </article>
        </div>
      </section>

      <section>
        <p className="kicker">The problem</p>
        <h2>This is not only a “we need more hospitals” problem.</h2>
        <p className="lede">Even when a doctor exists, a lot of women still delay the visit.</p>
        <div className="stats">
          <article>
            <strong>~74%</strong>
            <p>rural CHCs are short of obstetricians / gynecologists</p>
            <span>Rural Health Statistics, 2021–22</span>
          </article>
          <article>
            <strong>~60%</strong>
            <p>of women said they have trouble getting care for themselves</p>
            <span>NFHS-5</span>
          </article>
          <article>
            <strong>~31%</strong>
            <p>said there was no female health worker when they needed one</p>
            <span>NFHS-5</span>
          </article>
        </div>
        <ul className="points">
          <li>Talking about periods, fertility, or bleeding in a crowded clinic is uncomfortable, so many people wait.</li>
          <li>Booking is on one app, reports are PDFs on WhatsApp, cycle dates are in another app. The doctor never sees the full picture.</li>
          <li>Public telemedicine helped during COVID, but follow-up and old records often do not carry over to the next visit.</li>
          <li>If something feels urgent, most booking sites still treat it like a normal slot.</li>
        </ul>
      </section>

      <section>
        <p className="kicker">Aim</p>
        <h2>A simple, private website.</h2>
        <p className="lede">
          To make a simple, private website where a woman can find a gynecologist, consult her, keep prescriptions and reports in one login, track her cycle or pregnancy, and get moved up the queue if it is urgent.
        </p>
        <ol className="objectives">
          <li>Let her search and book a gynecologist for a clinic visit.</li>
          <li>Use the symptoms she enters to suggest a better-matched doctor.</li>
          <li>Store e-prescriptions and uploaded reports on her account.</li>
          <li>Let her see upcoming visits and old prescriptions in one place.</li>
          <li>Let her log periods and pregnancy dates, with basic reminders.</li>
          <li>Send urgent requests to the front of the list.</li>
          <li>Keep data behind logins — patient, doctor, admin see different things.</li>
          <li>Add a small, watched forum and doctor-written articles.</li>
        </ol>
      </section>

      <section>
        <p className="kicker">How it is handled</p>
        <h2>Stop the messy, public, scattered parts of getting gynae care.</h2>
        <p>SheCares is not trying to replace a hospital.</p>
        <div className="table-wrap">
          <table className="compare">
            <thead>
              <tr>
                <th>What goes wrong today</th>
                <th>What is on the site</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Hard to reach a specialist</td>
                <td>Online booking for a clinic visit. Show who is free and what they actually treat.</td>
              </tr>
              <tr>
                <td>Awkward to ask around</td>
                <td>She can search and book from home, without asking people or sitting in a clinic just to get a slot.</td>
              </tr>
              <tr>
                <td>Reports all over the place</td>
                <td>One file area on her account. The doctor she booked can open it; others cannot.</td>
              </tr>
              <tr>
                <td>Wrong doctor, wasted visit</td>
                <td>A short symptom form before booking, then a list of gynecologists who match that.</td>
              </tr>
              <tr>
                <td>Urgent cases wait</td>
                <td>An “urgent” mark that puts the request on top and pings available doctors.</td>
              </tr>
              <tr>
                <td>Worries about privacy</td>
                <td>Separate logins. Admin manages accounts, not medical notes. Passwords hashed, files stored encrypted.</td>
              </tr>
              <tr>
                <td>Random advice on the internet</td>
                <td>Forum is moderated. Health articles come from verified doctor accounts, not from any user.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <p className="kicker">After login</p>
        <h2>Everyone starts the same way. Then the screens split.</h2>
        <p>Urgent is only a flag on the booking, not a separate app.</p>
        <div className="flow-start">
          <span>Register / login</span>
          <span>Check who they are</span>
          <span>Open their home page</span>
        </div>
        <div className="grid-3 flow">
          <article className="card">
            <h3>If patient</h3>
            <ol>
              <li>Type symptoms (optional)</li>
              <li>Search or see suggested doctors</li>
              <li>Book or mark urgent</li>
              <li>Go for the clinic visit</li>
              <li>Get a prescription, save reports</li>
              <li>Update period / pregnancy log</li>
            </ol>
          </article>
          <article className="card">
            <h3>If doctor</h3>
            <ol>
              <li>Keep profile and free slots</li>
              <li>See today’s appointments</li>
              <li>Pick up urgent ones first</li>
              <li>Talk to the patient</li>
              <li>Write the prescription</li>
              <li>Add notes to her record</li>
            </ol>
          </article>
          <article className="card">
            <h3>If admin</h3>
            <ol>
              <li>Approve doctor sign-ups</li>
              <li>Remove junk from the forum</li>
              <li>See login / access logs</li>
              <li>Put up doctor articles</li>
              <li>Watch urgent-request delays</li>
              <li>Handle complaints</li>
            </ol>
          </article>
        </div>
      </section>
    </div>
  );
}
