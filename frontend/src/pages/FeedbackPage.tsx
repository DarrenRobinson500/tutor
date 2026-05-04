import React, { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetchJson } from "../utils/apiFetch"

interface Note {
  id: number;
  text: string;
  category: string | null;
  template: number | null;
  created_at: string;
  author: {
    id: number;
    first_name: string;
    last_name: string;
  };
}

export default function FeedbackPage() {
  const [text, setText] = useState("");
  const [category, setCategory] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);

  // Load existing feedback on mount
useEffect(() => {
  apiFetchJson("/api/notes/")
    .then(setNotes)
    .catch(err => console.error(err));
}, []);



  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const response = await fetch("/api/notes/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        text,
        category: category || null,
        template: templateId || null,
      }),
    });

    const newNote = await response.json();

    // Add new feedback to the top
    setNotes((prev) => [newNote, ...prev]);

    setSubmitted(true);
    setText("");
    setCategory("");
    setTemplateId("");
  };

  return (
  <Layout>
    <div className="container mt-4" style={{ maxWidth: 600 }}>
      <h1>Provide Feedback</h1>
      <p>Your feedback helps us improve the platform.</p>

      <form onSubmit={submit}>
        <div className="mb-3">
          <label className="form-label">Feedback</label>
          <textarea
            className="form-control"
            rows={5}
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Category (optional)</label>
          <input
            className="form-control"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="UX, Bug, Content, etc."
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Template ID (optional)</label>
          <input
            className="form-control"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            placeholder="If feedback relates to a specific template"
          />
        </div>

        <button className="btn btn-primary">Submit</button>
      </form>

      {submitted && (
        <div className="alert alert-success mt-3">
          Thank you for your feedback!
        </div>
      )}

      <hr className="my-4" />

      <h3>Previous Feedback</h3>

      {notes.length === 0 && <p>No feedback yet.</p>}

      <ul className="list-group mt-3">
        {notes.map((note) => (
          <li key={note.id} className="list-group-item">
            <blockquote className="blockquote mb-1">
              “{note.text}”
            </blockquote>
            <footer className="blockquote-footer">
              {note.author?.first_name} {note.author?.last_name} on{" "}
              {new Date(note.created_at).toLocaleString()}
            </footer>
          </li>
        ))}
      </ul>
    </div>
  </Layout>
  );
}