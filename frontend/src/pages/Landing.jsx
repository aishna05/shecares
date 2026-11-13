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
