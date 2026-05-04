import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface KnowledgeItem {
  id: number;
  title: string;
  text: string;
  skill_ids: number[];
}

export function KnowledgeListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");
  const uploadRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiFetch("/api/knowledge/")
      .then(r => r.json())
      .then(data => setItems(Array.isArray(data) ? data : (data.results ?? [])))
      .finally(() => setLoading(false));
  }, []);

  const filtered = items.filter(k =>
    k.title.toLowerCase().includes(search.toLowerCase()) ||
    k.text.toLowerCase().includes(search.toLowerCase())
  );

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    const form = new FormData();
    form.append("file", file);
    apiFetch("/api/knowledge/import_bulk/", { method: "POST", body: form })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setMessage(`Upload failed: ${data.error}`);
        } else {
          setMessage(`${data.status} (${data.count} items processed)`);
          apiFetch("/api/knowledge/")
            .then(r => r.json())
            .then(d => setItems(Array.isArray(d) ? d : (d.results ?? [])));
        }
      })
      .catch(() => setMessage("Upload failed"))
      .finally(() => setImporting(false));
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this knowledge item?")) return;
    setDeleting(id);
    await apiFetch(`/api/knowledge/${id}/`, { method: "DELETE" });
    setItems(prev => prev.filter(k => k.id !== id));
    setDeleting(null);
  };

  return (
    <Layout>
      <div className="container-fluid py-3" style={{ maxWidth: 900 }}>
        {message && <div className="alert alert-info">{message}</div>}
        <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
          <h4 className="mb-0 flex-grow-1">Knowledge</h4>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => uploadRef.current?.click()}
            disabled={importing}
          >
            {importing ? "Uploading…" : "Upload Knowledge"}
          </button>
          <input
            ref={uploadRef}
            type="file"
            accept=".yaml,.yml"
            className="d-none"
            onChange={handleUpload}
          />
          <Link to="/knowledge/new" className="btn btn-primary btn-sm">+ New</Link>
        </div>

        <input
          className="form-control mb-3"
          placeholder="Search by title or text…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ maxWidth: 400 }}
        />

        {loading && <p className="text-muted">Loading…</p>}

        {!loading && filtered.length === 0 && (
          <p className="text-muted">
            {search ? "No items match your search." : "No knowledge items yet."}
          </p>
        )}

        <div className="list-group">
          {filtered.map(k => (
            <div
              key={k.id}
              className="list-group-item list-group-item-action d-flex align-items-start gap-2 py-2"
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/knowledge/${k.id}`)}
            >
              <div className="flex-grow-1" style={{ minWidth: 0 }}>
                <div className="fw-semibold" style={{ fontSize: 15 }}>{k.title}</div>
                {k.text && (
                  <div
                    className="text-muted"
                    style={{ fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                  >
                    {k.text}
                  </div>
                )}
              </div>
              <button
                className="btn btn-outline-danger btn-sm flex-shrink-0"
                style={{ fontSize: 12 }}
                disabled={deleting === k.id}
                onClick={e => { e.stopPropagation(); handleDelete(k.id); }}
              >
                {deleting === k.id ? "…" : "Delete"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
