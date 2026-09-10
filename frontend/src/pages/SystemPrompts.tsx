import { useCallback, useEffect, useState } from "react";
import {
  createSystemPrompt,
  deleteSystemPrompt,
  listSystemPrompts,
  updateSystemPrompt,
  type SystemPrompt,
} from "../api/systemPrompts";
import PromptForm from "./PromptForm";

type Mode =
  | { kind: "closed" }
  | { kind: "create" }
  | { kind: "edit"; prompt: SystemPrompt };

export default function SystemPrompts() {
  const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
  const [mode, setMode] = useState<Mode>({ kind: "closed" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setPrompts(await listSystemPrompts());
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

  async function handleDelete(prompt: SystemPrompt) {
    setError(null);
    try {
      await deleteSystemPrompt(prompt.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <section>
      <h1>System Prompts</h1>
      {error && <p className="error">{error}</p>}

      {mode.kind === "closed" && (
        <button onClick={() => setMode({ kind: "create" })}>
          New System Prompt
        </button>
      )}

      {mode.kind === "create" && (
        <div className="card">
          <h2>Create System Prompt</h2>
          <PromptForm
            submitLabel="Create"
            onSubmit={async (data) => {
              await createSystemPrompt(data);
              setMode({ kind: "closed" });
              await refresh();
            }}
            onCancel={() => setMode({ kind: "closed" })}
          />
        </div>
      )}

      {mode.kind === "edit" && (
        <div className="card">
          <h2>Edit System Prompt</h2>
          <PromptForm
            initial={{ title: mode.prompt.title, content: mode.prompt.content }}
            submitLabel="Save"
            onSubmit={async (data) => {
              await updateSystemPrompt(mode.prompt.id, data);
              setMode({ kind: "closed" });
              await refresh();
            }}
            onCancel={() => setMode({ kind: "closed" })}
          />
        </div>
      )}

      <div className="card-list" style={{ marginTop: "1rem" }}>
        {prompts.length === 0 && mode.kind === "closed" && (
          <p className="notice">
            No system prompts yet. Create one to use in a Vision Profile.
          </p>
        )}
        {prompts.map((p) => (
          <div className="card" key={p.id}>
            <h2>{p.title}</h2>
            <p className="meta" style={{ whiteSpace: "pre-wrap" }}>
              {p.content}
            </p>
            <div className="actions">
              <button onClick={() => setMode({ kind: "edit", prompt: p })}>
                Edit
              </button>
              <button onClick={() => void handleDelete(p)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
