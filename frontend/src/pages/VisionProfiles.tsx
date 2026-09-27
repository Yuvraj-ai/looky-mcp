import { useCallback, useEffect, useState } from "react";
import type { SystemPrompt } from "../api/systemPrompts";
import {
  activateVisionProfile,
  createVisionProfile,
  deleteVisionProfile,
  listVisionProfiles,
  loadProfileOptions,
  updateVisionProfile,
  type VisionProfile,
  type VisionProfileInput,
} from "../api/visionProfiles";
import ProfileForm from "./ProfileForm";

type Mode =
  | { kind: "closed" }
  | { kind: "create" }
  | { kind: "edit"; profile: VisionProfile };

export default function VisionProfiles() {
  const [profiles, setProfiles] = useState<VisionProfile[]>([]);
  const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
  const [mode, setMode] = useState<Mode>({ kind: "closed" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([
        listVisionProfiles(),
        loadProfileOptions(),
      ]);
      setProfiles(p);
      setPrompts(s);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const promptTitle = (id: string) =>
    prompts.find((p) => p.id === id)?.title ?? "—";

  async function handleActivate(profile: VisionProfile) {
    setError(null);
    try {
      await activateVisionProfile(profile.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activation failed");
    }
  }

  async function handleDelete(profile: VisionProfile) {
    if (
      !window.confirm(
        `Are you sure you want to delete profile "${profile.name}"?`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await deleteVisionProfile(profile.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function handleSubmit(
    data: VisionProfileInput,
    editing: VisionProfile | null,
  ) {
    if (editing) {
      await updateVisionProfile(editing.id, data);
    } else {
      await createVisionProfile(data);
    }
    setMode({ kind: "closed" });
    await refresh();
  }

  const filteredProfiles = profiles.filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const pTitle = promptTitle(p.system_prompt_id).toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.model.toLowerCase().includes(q) ||
      p.endpoint.toLowerCase().includes(q) ||
      pTitle.includes(q)
    );
  });

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <section>
      <h1>Vision Profiles</h1>
      {error && <p className="error">{error}</p>}

      {mode.kind === "closed" && (
        <div className="section-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <button
              className="btn-primary"
              onClick={() => setMode({ kind: "create" })}
              disabled={prompts.length === 0}
            >
              New Vision Profile
            </button>
            {prompts.length === 0 && (
              <span className="notice">Create a System Prompt first.</span>
            )}
          </div>
          <input
            type="search"
            className="search-input"
            placeholder="Search vision profiles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      {mode.kind === "create" && (
        <div className="card">
          <h2>Create Vision Profile</h2>
          <ProfileForm
            prompts={prompts}
            submitLabel="Create Profile"
            onSubmit={(data) => handleSubmit(data, null)}
            onCancel={() => setMode({ kind: "closed" })}
          />
        </div>
      )}

      {mode.kind === "edit" && (
        <div className="card">
          <h2>Edit Vision Profile</h2>
          <ProfileForm
            prompts={prompts}
            initial={mode.profile}
            submitLabel="Save"
            onSubmit={(data) => handleSubmit(data, mode.profile)}
            onCancel={() => setMode({ kind: "closed" })}
          />
        </div>
      )}

      <div className="card-list" style={{ marginTop: "1rem" }}>
        {profiles.length === 0 && mode.kind === "closed" && (
          <p className="notice">No vision profiles yet.</p>
        )}
        {profiles.length > 0 && filteredProfiles.length === 0 && (
          <p className="notice">No vision profiles matching "{searchQuery}".</p>
        )}
        {filteredProfiles.map((p) => (
          <div className="card" key={p.id}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "0.5rem",
              }}
            >
              <h2 style={{ margin: 0 }}>{p.name}</h2>
              {p.is_active && <span className="badge badge-active">Active</span>}
            </div>
            <div className="meta">
              <span>Model: {p.model}</span>
              <span>Endpoint: {p.endpoint}</span>
              <span>System Prompt: {promptTitle(p.system_prompt_id)}</span>
              <span>API Key: {p.has_api_key ? "✓ Configured" : "Not set"}</span>
            </div>
            <div className="actions">
              {p.is_active ? (
                <button disabled>Active</button>
              ) : (
                <button
                  className="btn-primary"
                  onClick={() => void handleActivate(p)}
                >
                  Set Active
                </button>
              )}
              <button onClick={() => setMode({ kind: "edit", profile: p })}>
                Edit
              </button>
              <button
                className="btn-danger"
                onClick={() => void handleDelete(p)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
