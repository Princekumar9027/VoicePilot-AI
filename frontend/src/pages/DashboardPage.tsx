import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ConversationSummary } from "../services/apiClient";
import { useAuth } from "../stores/AuthContext";

interface Overview {
  conversations: number;
  messages: number;
  voice_messages: number;
  documents: number;
  tool_calls: number;
}

interface Usage {
  messages_per_day: { date: string; count: number }[];
  tool_usage: { tool: string; count: number }[];
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [recent, setRecent] = useState<ConversationSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Overview>("/analytics/overview"), api<Usage>("/analytics/usage"), api<ConversationSummary[]>("/conversations")])
      .then(([o, u, c]) => {
        setOverview(o);
        setUsage(u);
        setRecent(c.slice(0, 5));
      })
      .catch((err) => setError(err.message));
  }, []);

  const peak = Math.max(1, ...(usage?.messages_per_day.map((d) => d.count) ?? [1]));
  const cards = overview
    ? [
        ["Conversations", overview.conversations],
        ["Messages", overview.messages],
        ["Voice messages", overview.voice_messages],
        ["Knowledge documents", overview.documents],
        ["Tool calls", overview.tool_calls],
      ]
    : [];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Welcome back, {user?.full_name.split(" ")[0]}</h1>
          <p className="muted">Here is what your assistant has been doing.</p>
        </div>
        <div className="actions">
          <Link className="primary-btn small" to="/voice">Start voice chat</Link>
          <Link className="ghost-btn" to="/knowledge">Upload knowledge</Link>
        </div>
      </header>

      {error && <div className="form-error">{error}</div>}

      <div className="stat-grid">
        {cards.map(([label, value]) => (
          <div className="stat" key={label as string}>
            <span className="stat-value">{value}</span>
            <span className="muted">{label}</span>
          </div>
        ))}
      </div>

      <div className="two-col">
        <section className="panel">
          <h3>Messages, last 7 days</h3>
          <div className="bars">
            {usage?.messages_per_day.map((day) => (
              <div className="bar-col" key={day.date}>
                <span className="bar-count">{day.count}</span>
                <div className="bar" style={{ height: `${(day.count / peak) * 100}%` }} />
                <small>{day.date.slice(5)}</small>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <h3>Tool usage</h3>
          {usage && usage.tool_usage.length === 0 && <p className="muted">No tools used yet. Ask the agent to calculate something.</p>}
          <ul className="plain-list">
            {usage?.tool_usage.map((tool) => (
              <li key={tool.tool}><span>{tool.tool}</span><strong>{tool.count}</strong></li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel">
        <h3>Recent conversations</h3>
        {recent.length === 0 && <p className="muted">No conversations yet. Start one from the Voice Agent.</p>}
        <ul className="plain-list">
          {recent.map((c) => (
            <li key={c.id}><Link to={`/voice?c=${c.id}`}>{c.title}</Link><small>{new Date(c.updated_at).toLocaleString()}</small></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
