import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../stores/AuthContext";

export default function OAuthCallbackPage() {
  const { completeOAuth } = useAuth();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const access = params.get("access_token");
    const refresh = params.get("refresh_token");
    window.history.replaceState(null, "", window.location.pathname);
    if (!access || !refresh) {
      setFailed(true);
      return;
    }
    completeOAuth(access, refresh)
      .then(() => navigate("/", { replace: true }))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <div className="center-screen">Sign-in failed. <a href="/login">Back to login</a></div>;
  return <div className="center-screen">Signing you in...</div>;
}
