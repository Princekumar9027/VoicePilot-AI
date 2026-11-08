import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Mic, BookOpen, ShieldCheck, LogOut } from "lucide-react";
import { useAuth } from "../stores/AuthContext";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const links = [
    { to: "/", label: "Dashboard", icon: <LayoutDashboard size={20} />, end: true },
    { to: "/voice", label: "Voice Agent", icon: <Mic size={20} /> },
    { to: "/knowledge", label: "Knowledge Base", icon: <BookOpen size={20} /> },
  ];
  if (user?.role === "ADMIN") links.push({ to: "/admin", label: "Admin Panel", icon: <ShieldCheck size={20} />, end: false });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Mic size={20} /><span>VoicePilot AI</span></div>
        <nav>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              {link.icon}<span>{link.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="who">
            <strong>{user?.full_name}</strong>
            <small>{user?.email}</small>
          </div>
          <button className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut size={18} /></button>
        </div>
      </aside>
      <main className="content"><Outlet /></main>
    </div>
  );
}
