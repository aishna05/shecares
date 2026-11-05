import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorNote, PageHead } from "../ui";

export function ArticleList() {
  const { user } = useAuth();
  const [articles, setArticles] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", summary: "", body: "", author_id: "" });

  function load() {
    api("/articles/").then(setArticles).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
    if (user.role === "admin") {
      api("/admin/doctors/").then((rows) => setDoctors(rows.filter((doctor) => doctor.is_approved))).catch(() => {});
    }
  }, [user.role]);

  async function publish(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/articles/", { method: "POST", body: { ...form, author_id: Number(form.author_id), is_published: true } });
      setForm({ title: "", summary: "", body: "", author_id: "" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggle(article) {
    await api(`/articles/${article.id}/`, { method: "PUT", body: { is_published: !article.is_published } });
    load();
  }

  return (
    <div>
      <PageHead kicker="Articles" title="Written by verified doctors" lede="Patients can read. They cannot publish. An admin can put an article up under an approved doctor's name, or take one down." />
      <ErrorNote>{error}</ErrorNote>
      {user.role === "admin" && (
        <form className="card form" onSubmit={publish}>
          <h2>Put up a doctor article</h2>
          <label className="field">
            <span>Doctor</span>
            <select value={form.author_id} onChange={(event) => setForm({ ...form, author_id: event.target.value })} required>
              <option value="">Choose</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>{doctor.name} · {doctor.specialty}</option>
              ))}
            </select>
          </label>
          <label className="field"><span>Title</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
          <label className="field"><span>Summary</span><input value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} required /></label>
          <label className="field"><span>Article</span><textarea rows={5} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} required /></label>
          <button className="btn" type="submit">Publish</button>
        </form>
      )}
      <div className="stack">
        {articles.map((article) => (
          <article className="card" key={article.id}>
            <p className="kicker">{article.author_name} · {article.author_specialty}{article.is_published ? "" : " · draft"}</p>
            <h2><Link to={`/articles/${article.id}`}>{article.title}</Link></h2>
            <p>{article.summary}</p>
            {user.role === "admin" && (
              <button className="btn small secondary" type="button" onClick={() => toggle(article)}>
                {article.is_published ? "Unpublish" : "Publish"}
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

export function ArticleDetail() {
  const { id } = useParams();
  const [article, setArticle] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/articles/${id}/`).then(setArticle).catch((err) => setError(err.message));
  }, [id]);

  if (!article) return <ErrorNote>{error || "Loading the article…"}</ErrorNote>;
  return (
    <article className="narrow">
      <PageHead kicker={`${article.author_name} · ${article.author_specialty}`} title={article.title} lede={article.summary} />
      {article.body.split("\n\n").map((paragraph) => (
        <p className="prose" key={paragraph}>{paragraph}</p>
      ))}
      <p className="banner warn">This article is general information from a doctor account. It is not a diagnosis and it is not a prescription for you.</p>
    </article>
  );
}
