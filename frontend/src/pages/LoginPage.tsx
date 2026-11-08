import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, Mic, BookOpen, Wrench, ShieldCheck } from "lucide-react";
import Orb from "../components/Orb";
import Waveform from "../components/Waveform";
import { useAuth } from "../stores/AuthContext";
import { api } from "../services/apiClient";

type Providers = { google: boolean; github: boolean; microsoft: boolean };

const oauthErrors: Record<string, string> = {
  oauth_failed: "Sign-in with that provider did not complete. Try again.",
  no_email: "The provider did not share an email address.",
  unverified_email: "That provider email is not verified, so it cannot be linked.",
  disabled: "This account is disabled.",
};

function strength(password: string) {
  const checks = [/.{8,}/, /[A-Z]/, /[a-z]/, /\d/, /[^A-Za-z0-9]/];
  return checks.filter((rule) => rule.test(password)).length;
}

const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
    <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" />
    <path fill="#FBBC05" d="M10.5 28.7c-.5-1.5-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.4 0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z" />
    <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
  </svg>
);

const GithubIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.15.08 1.77 1.19 1.77 1.19 1.03 1.77 2.69 1.26 3.35.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z" />
  </svg>
);

const MicrosoftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="1" y="1" width="10" height="10" fill="#F25022" />
    <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
    <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
    <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
  </svg>
);

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [providers, setProviders] = useState<Providers | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState(oauthErrors[params.get("error") ?? ""] ?? "");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Providers>("/auth/providers")
      .then(setProviders)
      .catch(() => setProviders({ google: false, github: false, microsoft: false }));
  }, []);

  if (user) return <Navigate to="/" replace />;

  const score = strength(password);
  const labels = ["Too short", "Weak", "Fair", "Good", "Strong", "Excellent"];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (mode === "register") {
      if (password !== confirm) return setError("Passwords do not match.");
      if (score < 5) return setError("Password needs 8+ characters with upper, lower, number and a special character.");
      if (!accepted) return setError("Accept the Terms and Privacy Policy to continue.");
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(fullName, email, phone, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const social = [
    { key: "google" as const, label: "Continue with Google", icon: <GoogleIcon /> },
    { key: "github" as const, label: "Continue with GitHub", icon: <GithubIcon /> },
    { key: "microsoft" as const, label: "Continue with Microsoft", icon: <MicrosoftIcon /> },
  ];

  return (
    <div className="auth-shell">
      <section className="auth-hero">
        <div className="brand">
          <Mic size={22} />
          <span>VoicePilot AI</span>
        </div>
        <div className="hero-stage">
          <Orb state="speaking" size={260} />
          <Waveform active />
        </div>
        <h1>Talk to your business. It answers from your own documents.</h1>
        <ul className="feature-list">
          <li><Mic size={18} /> Hands-free voice conversations</li>
          <li><BookOpen size={18} /> Answers with the source document named</li>
          <li><Wrench size={18} /> Safe tools: calculator, time, support tickets</li>
          <li><ShieldCheck size={18} /> Rotating sessions and login lockout</li>
        </ul>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="muted">{mode === "login" ? "Sign in to continue to your workspace." : "Start with a free workspace in under a minute."}</p>

          <div className="social-stack">
            {social.map((item) => {
              const enabled = providers?.[item.key] ?? false;
              return (
                <button
                  key={item.key}
                  type="button"
                  className="social-btn"
                  disabled={!enabled}
                  title={enabled ? item.label : "Not configured. Add credentials to .env"}
                  onClick={() => (window.location.href = `/api/auth/${item.key}`)}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {!enabled && providers && <em>Not configured</em>}
                </button>
              );
            })}
          </div>

          <div className="divider"><span>or use email</span></div>

          <form onSubmit={submit} noValidate>
            {mode === "register" && (
              <>
                <label>Full name
                  <input value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" required />
                </label>
                <label>Phone number
                  <input value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" inputMode="tel" />
                </label>
              </>
            )}
            <label>Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            </label>
            <label>Password
              <div className="password-row">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                />
                <button type="button" className="icon-btn" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>

            {mode === "register" && (
              <>
                <div className="strength" aria-live="polite">
                  <div className="strength-bar"><span style={{ width: `${(score / 5) * 100}%` }} data-level={score} /></div>
                  <small>{password ? labels[score] : "Use 8+ characters with upper, lower, number and symbol"}</small>
                </div>
                <label>Confirm password
                  <input type={showPassword ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
                </label>
                <label className="check">
                  <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
                  <span>I accept the Terms and Privacy Policy</span>
                </label>
              </>
            )}

            {error && <div className="form-error" role="alert">{error}</div>}

            <button className="primary-btn" type="submit" disabled={busy}>
              {busy ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="switch">
            {mode === "login" ? "New to VoicePilot?" : "Already have an account?"}{" "}
            <button type="button" className="link-btn" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </div>
      </section>
    </div>
  );
}
