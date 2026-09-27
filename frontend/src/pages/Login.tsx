import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import GitHubCard from "./GitHubCard";
import LookyInfoModal from "./LookyInfoModal";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showInfo, setShowInfo] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <video
        className="login-video"
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
        autoPlay
        loop
        muted
        playsInline
        aria-hidden="true"
      >
        <source
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260808_064556_051587f1-74a1-4336-8c05-4dde3594ed05.mp4"
          type="video/mp4"
        />
      </video>
      <div className="login-video-overlay" aria-hidden="true" />
      <form className="login-card" onSubmit={onSubmit}>
        <h1>Looky MCP</h1>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn-primary" type="submit" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
        <a className="google-link" href="/api/auth/google/start">
          Sign in with Google
        </a>
        <div className="login-signup-note">
          <span className="signup-note-badge">Note</span>
          <span>
            No public signup. Accounts are provisioned via <code>create_user.py</code> on the server or pre-authorized Google accounts.
          </span>
        </div>
      </form>
      <div className="login-footer-left">
        <GitHubCard className="github-card-login" />
      </div>
      <div className="login-bottom-center">
        <button
          type="button"
          className="what-is-looky-btn"
          onClick={() => setShowInfo(true)}
          aria-haspopup="dialog"
          title="Learn more about Looky MCP"
        >
          <span className="what-is-looky-icon">💡</span>
          What is Looky MCP??
          <span className="what-is-looky-chevron" aria-hidden="true">▲</span>
        </button>
      </div>

      <LookyInfoModal isOpen={showInfo} onClose={() => setShowInfo(false)} />
    </div>
  );
}
