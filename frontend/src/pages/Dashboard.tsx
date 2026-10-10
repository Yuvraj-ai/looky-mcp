import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboard, type DashboardResponse } from "../api/dashboard";

const errorLabels: Record<string, string> = {
  invalid_image: "Invalid image",
  rate_limited: "Rate limit reached",
  busy: "Too many concurrent requests",
  no_active_profile: "No active profile",
  provider_authentication_failed: "Provider authentication failed",
  provider_rate_limited: "Provider rate limit reached",
  provider_timeout: "Provider timed out",
  provider_unavailable: "Provider unavailable",
  provider_configuration_error: "Provider configuration error",
  provider_rejected_request: "Provider rejected the request",
  invalid_provider_response: "Invalid provider response",
  cancelled: "Request cancelled",
  request_failed: "Request failed",
};

function formatDuration(milliseconds: number | null): string {
  if (milliseconds === null) return "—";
  return milliseconds >= 1000
    ? `${(milliseconds / 1000).toFixed(1)} s`
    : `${milliseconds} ms`;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getDashboard());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading && !data)
    return <div className="loading">Loading dashboard...</div>;
  if (error && !data) {
    return (
      <section>
        <h1>Dashboard</h1>
        <p className="error">{error}</p>
        <button onClick={() => void refresh()}>Try again</button>
      </section>
    );
  }
  if (!data) return null;

  const { setup, activity } = data;
  const successRate = activity.total_7d
    ? Math.round((activity.succeeded_7d / activity.total_7d) * 100)
    : null;
  const maxDaily = Math.max(1, ...activity.daily.map((day) => day.total));

  return (
    <section className="dashboard">
      <div className="dashboard-heading">
        <div>
          <h1>Dashboard</h1>
          <p className="dashboard-subtitle">Your setup and recent activity</p>
        </div>
        <button onClick={() => void refresh()} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      <h2 className="dashboard-section-title">Your setup</h2>
      <div className="dashboard-grid dashboard-setup-grid">
        <article className="card dashboard-card">
          <span className="dashboard-label">Active vision profile</span>
          <strong>{setup.active_profile_name ?? "None selected"}</strong>
          <span className="dashboard-detail">
            {setup.active_model ?? "Choose a profile to start"}
          </span>
          <Link to="/vision-profiles">Manage profiles</Link>
        </article>
        <article className="card dashboard-card">
          <span className="dashboard-label">Configuration</span>
          <strong>
            {setup.profile_count}{" "}
            {setup.profile_count === 1 ? "profile" : "profiles"}
          </strong>
          <span className="dashboard-detail">
            {setup.prompt_count}{" "}
            {setup.prompt_count === 1 ? "system prompt" : "system prompts"}
          </span>
          <Link to="/system-prompts">Manage prompts</Link>
        </article>
        <article className="card dashboard-card">
          <span className="dashboard-label">MCP connection</span>
          <strong
            className={setup.mcp_configured ? "status-good" : "status-muted"}
          >
            {setup.mcp_configured ? "Configured" : "Not configured"}
          </strong>
          <span className="dashboard-detail">Personal access credential</span>
          <Link to="/mcp-access">MCP access</Link>
        </article>
      </div>

      <h2 className="dashboard-section-title">Last 7 days</h2>
      <div className="dashboard-grid dashboard-metrics-grid">
        <article className="card dashboard-card">
          <span className="dashboard-label">Requests</span>
          <strong>{activity.total_7d}</strong>
        </article>
        <article className="card dashboard-card">
          <span className="dashboard-label">Success rate</span>
          <strong>{successRate === null ? "—" : `${successRate}%`}</strong>
        </article>
        <article className="card dashboard-card">
          <span className="dashboard-label">Failed requests</span>
          <strong>{activity.failed_7d}</strong>
        </article>
        <article className="card dashboard-card">
          <span className="dashboard-label">Average response</span>
          <strong>{formatDuration(activity.average_duration_ms)}</strong>
        </article>
      </div>

      <article className="card dashboard-chart-card">
        <h2>Daily requests</h2>
        <div
          className="dashboard-chart"
          role="img"
          aria-label="Requests per day for the last seven days"
        >
          {activity.daily.map((day) => {
            const successHeight = (day.succeeded / maxDaily) * 100;
            const failedHeight = (day.failed / maxDaily) * 100;
            return (
              <div className="dashboard-chart-day" key={day.date}>
                <span className="dashboard-chart-count">{day.total}</span>
                <div
                  className="dashboard-bar-track"
                  title={`${day.succeeded} successful, ${day.failed} failed`}
                >
                  <span
                    className="dashboard-bar-success"
                    style={{ height: `${successHeight}%` }}
                  />
                  <span
                    className="dashboard-bar-failed"
                    style={{ height: `${failedHeight}%` }}
                  />
                </div>
                <time dateTime={day.date}>
                  {new Date(`${day.date}T00:00:00`).toLocaleDateString(
                    undefined,
                    { weekday: "short" },
                  )}
                </time>
              </div>
            );
          })}
        </div>
        <p className="dashboard-chart-legend">
          <span>
            <i className="legend-success" /> Successful
          </span>
          <span>
            <i className="legend-failed" /> Failed
          </span>
        </p>
      </article>

      <article className="card dashboard-requests-card">
        <h2>Recent requests</h2>
        {activity.recent.length === 0 ? (
          <p className="notice">Your MCP requests will appear here.</p>
        ) : (
          <div className="dashboard-table-wrap">
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Tool</th>
                  <th>Profile / model</th>
                  <th>Duration</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {activity.recent.map((request) => (
                  <tr key={request.id}>
                    <td>{new Date(request.created_at).toLocaleString()}</td>
                    <td>{request.mode === "ocr" ? "OCR" : "Describe image"}</td>
                    <td>
                      {request.profile_name ?? "—"}
                      {request.model && (
                        <span className="dashboard-detail">
                          {request.model}
                        </span>
                      )}
                    </td>
                    <td>{formatDuration(request.duration_ms)}</td>
                    <td>
                      <span
                        className={
                          request.succeeded ? "status-good" : "status-bad"
                        }
                      >
                        {request.succeeded
                          ? "Succeeded"
                          : (errorLabels[request.error_code ?? ""] ??
                            "Request failed")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
