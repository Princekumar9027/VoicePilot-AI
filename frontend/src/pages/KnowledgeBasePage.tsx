import { ChangeEvent, useEffect, useState } from "react";
import { Trash2, Upload, Search } from "lucide-react";
import { api, KnowledgeDocument } from "../services/apiClient";

interface Match {
  source: string;
  content: string;
  score: number;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<Match[] | null>(null);

  const load = () => api<KnowledgeDocument[]>("/documents").then(setDocuments).catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, []);

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const body = new FormData();
      body.append("file", file);
      await api("/documents/upload", { method: "POST", body });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const remove = async (id: string) => {
    await api(`/documents/${id}`, { method: "DELETE" });
    load();
  };

  const runSearch = async () => {
    if (!query.trim()) return;
    setError("");
    try {
      const data = await api<{ matches: Match[] }>(`/documents/search?q=${encodeURIComponent(query)}`);
      setMatches(data.matches);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Knowledge base</h1>
          <p className="muted">Upload PDF, TXT or DOCX files up to 10 MB. The agent answers from them and names the source.</p>
        </div>
        <label className="primary-btn small file-btn">
          <Upload size={16} /> {uploading ? "Processing..." : "Upload document"}
          <input type="file" accept=".pdf,.txt,.docx" onChange={upload} disabled={uploading} hidden />
        </label>
      </header>

      {error && <div className="form-error" role="alert">{error}</div>}

      <section className="panel">
        <div className="search-row">
          <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runSearch()} placeholder="Search your documents" />
          <button className="ghost-btn" onClick={runSearch}><Search size={16} /> Search</button>
        </div>
        {matches && matches.length === 0 && <p className="muted">Nothing relevant found.</p>}
        {matches?.map((m, i) => (
          <div className="match" key={i}>
            <strong>{m.source}</strong> <small>relevance {m.score}</small>
            <p>{m.content.slice(0, 300)}</p>
          </div>
        ))}
      </section>

      <section className="panel table-wrap">
        <table>
          <thead>
            <tr><th>Name</th><th>Type</th><th>Size</th><th>Uploaded</th><th>Status</th><th>Chunks</th><th /></tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td>{d.file_type.toUpperCase()}</td>
                <td>{formatSize(d.size_bytes)}</td>
                <td>{new Date(d.created_at).toLocaleDateString()}</td>
                <td><span className={`badge ${d.status}`} title={d.error ?? ""}>{d.status}</span></td>
                <td>{d.chunk_count}</td>
                <td><button className="icon-btn" onClick={() => remove(d.id)} aria-label={`Delete ${d.name}`}><Trash2 size={16} /></button></td>
              </tr>
            ))}
            {documents.length === 0 && <tr><td colSpan={7} className="muted">No documents yet. Upload one to give the agent knowledge.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
