import { useEffect, useState } from "react";
import { api, User } from "../services/apiClient";
import { useAuth } from "../stores/AuthContext";

interface AuditEntry {
  id: string;
  actor_id: string | null;
  action: string;
  target: string | null;
  created_at: string;
}

export default function AdminPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");

  const load = () =>
    Promise.all([api<User[]>("/admin/users"), api<AuditEntry[]>("/admin/audit-logs")])
      .then(([u, l]) => {
        setUsers(u);
        setLogs(l);
      })
      .catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, []);

  const patch = async (id: string, body: object) => {
    setError("");
    try {
      await api(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  return (
    <div className="page">
      <header className="page-head"><div><h1>Admin panel</h1><p className="muted">Every change here is written to the audit log.</p></div></header>
      {error && <div className="form-error">{error}</div>}
      <section className="panel table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th>Last login</th><th /></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} disabled={u.id === me?.id} onChange={(e) => patch(u.id, { role: e.target.value })}>
                    <option>USER</option><option>SUPPORT_AGENT</option><option>ADMIN</option>
                  </select>
                </td>
                <td><span className={`badge ${u.is_active ? "completed" : "failed"}`}>{u.is_active ? "active" : "disabled"}</span></td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td>{u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}</td>
                <td><button className="ghost-btn" disabled={u.id === me?.id} onClick={() => patch(u.id, { is_active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel table-wrap">
        <h3>Audit log</h3>
        <table>
          <thead><tr><th>When</th><th>Action</th><th>Target</th><th>Actor</th></tr></thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}><td>{new Date(l.created_at).toLocaleString()}</td><td>{l.action}</td><td>{l.target}</td><td>{l.actor_id ?? "system"}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
