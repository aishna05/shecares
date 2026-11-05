export default function About() {
  return (
    <article className="story narrow">
      <p className="kicker">Methodology</p>
      <h1>Write it down, design the split, then build one module at a time.</h1>
      <p className="lede">
        Normal software project order. The site will not diagnose illness. If the first version works, success looks like this: a booking happens, the doctor writes a prescription, and nobody else’s file is visible.
      </p>
      <div className="grid-2">
        <article className="card">
          <h3>1. Write it down</h3>
          <p>List the pages, the three roles, and a few sample patients. Note what the site will not do.</p>
        </article>
        <article className="card">
          <h3>2. Design</h3>
          <p>Screens, tables for users, doctors, slots, records, and the tracker, and a permission list.</p>
        </article>
        <article className="card">
          <h3>3. Build</h3>
          <p>React + Vite for the UI. Django for login, booking, and prescriptions. SQL for the data.</p>
        </article>
        <article className="card">
          <h3>4. Check</h3>
          <p>Try booking. Make sure patient A cannot open patient B’s reports. Try the urgent flag.</p>
        </article>
      </div>
      <h2>References</h2>
      <ul className="points">
        <li>MoHFW, Rural Health Statistics 2021–22 — specialist shortfall at rural CHCs (gynecologists ~74%).</li>
        <li>IIPS & MoHFW, National Family Health Survey (NFHS-5), 2019–21 — women reporting trouble getting care, and missing female providers.</li>
        <li>Jain et al., “Reimagining India’s National Telemedicine Service…”, Lancet Regional Health – SE Asia, 2024 — gaps in follow-up and records.</li>
        <li>MoHFW / MCI, Telemedicine Practice Guidelines, March 2020.</li>
        <li>Digital Personal Data Protection Act, 2023 — why health data is treated as something to lock down.</li>
        <li>
          Project repo: <a href="https://github.com/SheCares-SE/SheCares">github.com/SheCares-SE/SheCares</a>
        </li>
      </ul>
      <p className="banner warn">
        This will not diagnose anything, and it is not an emergency ward. If someone is in real trouble they still go to a hospital.
      </p>
    </article>
  );
}
