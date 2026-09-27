import { useCallback, useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";
import {
  createSystemPrompt,
  deleteSystemPrompt,
  listSystemPrompts,
  updateSystemPrompt,
  type SystemPrompt,
} from "../api/systemPrompts";
import ExtraInstructionsCard from "./ExtraInstructionsCard";
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
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

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
    if (
      !window.confirm(
        `Are you sure you want to delete system prompt "${prompt.title}"?`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await deleteSystemPrompt(prompt.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  const fuse = useMemo(() => {
    return new Fuse(prompts, {
      keys: [
        { name: "title", weight: 0.7 },
        { name: "content", weight: 0.3 },
      ],
      threshold: 0.35,
      ignoreLocation: true,
      minMatchCharLength: 2,
    });
  }, [prompts]);

  const filteredPrompts = useMemo(() => {
    if (!searchQuery.trim()) return prompts;
    return fuse.search(searchQuery.trim()).map((res) => res.item);
  }, [fuse, prompts, searchQuery]);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <section>
      <h1>System Prompts</h1>
      {error && <p className="error">{error}</p>}

      <ExtraInstructionsCard />

      {mode.kind === "closed" && (
        <div className="section-toolbar">
          <button className="btn-primary" onClick={() => setMode({ kind: "create" })}>
            New System Prompt
          </button>
          <input
            type="search"
            className="search-input"
            placeholder="Search system prompts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
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
        {prompts.length > 0 && filteredPrompts.length === 0 && (
          <p className="notice">
            No system prompts matching "{searchQuery}".
          </p>
        )}
        {filteredPrompts.map((p) => {
          const isExpanded = expandedIds.has(p.id);
          const isLong = p.content.length > 240;
          return (
            <div className="card prompt-card" key={p.id}>
              <h2>{p.title}</h2>
              <div className={`prompt-content ${isExpanded ? "expanded" : ""}`}>
                {p.content}
              </div>
              <div className="actions">
                <button onClick={() => setMode({ kind: "edit", prompt: p })}>
                  Edit
                </button>
                {isLong && (
                  <button onClick={() => toggleExpand(p.id)}>
                    {isExpanded ? "Collapse" : "Expand"}
                  </button>
                )}
                <button
                  className="btn-danger"
                  onClick={() => void handleDelete(p)}
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
