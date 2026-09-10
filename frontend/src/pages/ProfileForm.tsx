import { useState } from "react";
import type { SystemPrompt } from "../api/systemPrompts";
import type { VisionProfile, VisionProfileInput } from "../api/visionProfiles";

interface Props {
  prompts: SystemPrompt[];
  initial?: VisionProfile;
  submitLabel: string;
  onSubmit: (data: VisionProfileInput) => Promise<void>;
  onCancel: () => void;
}

export default function ProfileForm({
  prompts,
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [endpoint, setEndpoint] = useState(initial?.endpoint ?? "");
  const [model, setModel] = useState(initial?.model ?? "");
  const [apiKey, setApiKey] = useState("");
  const [promptId, setPromptId] = useState(initial?.system_prompt_id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await onSubmit({
        name,
        endpoint,
        model,
        api_key: initial ? apiKey : apiKey, // edit: "" = keep existing
        system_prompt_id: promptId,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-grid">
        <label>
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={200}
          />
        </label>
        <label>
          Endpoint / Base URL
          <input
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="https://api.provider.com/v1"
            required
          />
        </label>
        <label>
          Model
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="vision-model-name"
            required
          />
        </label>
        <label>
          API Key{" "}
          {initial && <span className="notice">(blank = keep current)</span>}
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={initial ? "unchanged" : "sk-..."}
            required={!initial}
          />
        </label>
        <label>
          System Prompt
          <select
            value={promptId}
            onChange={(e) => setPromptId(e.target.value)}
            required
          >
            <option value="" disabled>
              Select System Prompt
            </option>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={busy}>
          {submitLabel}
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
