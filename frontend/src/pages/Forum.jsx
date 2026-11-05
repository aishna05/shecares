import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { prettyDate } from "../format";
import { Empty, ErrorNote, Field, PageHead } from "../ui";

export function ForumList() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  function load() {
    const path = user.role === "admin" ? "/forum/posts/?all=1" : "/forum/posts/";
    return api(path).then(setPosts).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, [user.role]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/forum/posts/", { method: "POST", body: { title, body } });
      setTitle("");
      setBody("");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <PageHead kicker="Forum" title="A small, watched forum" lede="Posts stay on the site only if an admin leaves them up. This is not a consult and it is not a diagnosis." />
      <ErrorNote>{error}</ErrorNote>
      <form className="card form" onSubmit={submit}>
        <Field label="Title">
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </Field>
        <Field label="Message">
          <textarea value={body} onChange={(event) => setBody(event.target.value)} rows={4} required />
        </Field>
        <button className="btn" type="submit">Post</button>
      </form>
      <div className="stack">
        {posts.length === 0 && <Empty>No posts yet.</Empty>}
        {posts.map((post) => (
          <article className={post.is_removed ? "card removed" : "card"} key={post.id}>
            <p className="kicker">{post.author.name}{post.author.verified ? " · verified doctor" : ""} · {prettyDate(post.created_at.slice(0, 10))}</p>
            <h2><Link to={`/forum/${post.id}`}>{post.title}</Link></h2>
            <p>{post.body}</p>
            {post.is_removed && <p className="badge">Removed · {post.removed_reason}</p>}
            <p className="muted">{post.comment_count} comments</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export function ForumThread() {
  const { id } = useParams();
  const { user } = useAuth();
  const [post, setPost] = useState(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  function load() {
    return api(`/forum/posts/${id}/`).then(setPost).catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, [id]);

  async function comment(event) {
    event.preventDefault();
    try {
      setPost(await api(`/forum/posts/${id}/comments/`, { method: "POST", body: { body } }));
      setBody("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function moderate(action) {
    try {
      setPost(await api(`/forum/posts/${id}/moderate/`, { method: "POST", body: { action, reason: "Removed from the forum" } }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function moderateComment(commentId, action) {
    try {
      await api(`/forum/comments/${commentId}/moderate/`, { method: "POST", body: { action, reason: "Removed from the forum" } });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!post) return <ErrorNote>{error || "Loading the post…"}</ErrorNote>;

  return (
    <article>
      <PageHead kicker={post.author.name} title={post.title} />
      <ErrorNote>{error}</ErrorNote>
      {post.is_removed && <p className="banner warn">Removed from the public forum. {post.removed_reason}</p>}
      <p className="prose">{post.body}</p>
      {user.role === "admin" && (
        <div className="row">
          <button className="btn small secondary" type="button" onClick={() => moderate("remove")}>Remove post</button>
          <button className="btn small secondary" type="button" onClick={() => moderate("restore")}>Restore post</button>
        </div>
      )}
      <h2>Comments</h2>
      <div className="stack">
        {post.comments.length === 0 && <Empty>No comments yet.</Empty>}
        {post.comments.map((item) => (
          <article className={item.is_removed ? "card removed" : "card"} key={item.id}>
            <p className="kicker">{item.author.name}{item.author.verified ? " · verified doctor" : ""}</p>
            <p>{item.body}</p>
            {user.role === "admin" && (
              <button className="btn small secondary" type="button" onClick={() => moderateComment(item.id, item.is_removed ? "restore" : "remove")}>
                {item.is_removed ? "Restore comment" : "Remove comment"}
              </button>
            )}
          </article>
        ))}
      </div>
      {!post.is_removed && (
        <form className="card form" onSubmit={comment}>
          <Field label="Add a comment">
            <textarea value={body} onChange={(event) => setBody(event.target.value)} rows={3} required />
          </Field>
          <button className="btn" type="submit">Comment</button>
        </form>
      )}
    </article>
  );
}
