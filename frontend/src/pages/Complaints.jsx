import { useEffect, useState } from "react";
import { api } from "../api";
import { Empty, ErrorNote, Field, PageHead } from "../ui";

export default function Complaints() {
  const [rows, setRows] = useState([]);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  function load() {
    api("/complaints/").then(setRows).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/complaints/", { method: "POST", body: { subject, body } });
      setSubject("");
      setBody("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Complaint" title="Tell the admin what went wrong" lede="Complaints are about the site: a slot, a post, an account. Do not attach medical files here. Admin staff cannot open those anyway." />
      <ErrorNote>{error}</ErrorNote>
      <form className="card form" onSubmit={submit}>
        <Field label="Subject"><input value={subject} onChange={(event) => setSubject(event.target.value)} required /></Field>
        <Field label="What happened"><textarea rows={4} value={body} onChange={(event) => setBody(event.target.value)} required /></Field>
        <button className="btn" type="submit">Send</button>
      </form>
      <div className="stack">
        {rows.length === 0 && <Empty>You have not raised a complaint.</Empty>}
        {rows.map((row) => (
          <article className="card" key={row.id}>
            <p className="kicker">{row.status}</p>
            <h2>{row.subject}</h2>
            <p>{row.body}</p>
            {row.admin_note && <p className="muted">Admin: {row.admin_note}</p>}
          </article>
        ))}
      </div>
    </div>
  );
}
