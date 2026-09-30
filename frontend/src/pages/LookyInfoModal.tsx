import { useEffect, useState } from "react";
import systemPromptsGuideImg from "../assets/guide/system_prompts_guide.png";
import visionProfilesGuideImg from "../assets/guide/vision_profiles_guide.png";
import mcpAccessGuideImg from "../assets/guide/mcp_access_guide.png";

interface LookyInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type Tab = "about" | "how-to-use";

export default function LookyInfoModal({ isOpen, onClose }: LookyInfoModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>("about");

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="looky-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="looky-modal-title"
    >
      <div
        className="looky-modal-sheet"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header bar */}
        <div className="looky-modal-header">
          <div className="looky-modal-header-left">
            <div className="looky-brand-badge">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="4" />
                <line x1="21.17" y1="8" x2="12" y2="8" />
                <line x1="3.95" y1="6.06" x2="8.54" y2="14" />
                <line x1="10.88" y1="21.94" x2="15.46" y2="14" />
              </svg>
              <h2 id="looky-modal-title"><span className="looky-brand-name">Looky</span> MCP</h2>
            </div>
            <span className="looky-modal-tagline">Giving Eyes to Smart Non-Vision Open-Source Models</span>
          </div>

          <div className="looky-modal-nav">
            <div className="looky-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "about"}
                className={`looky-tab-btn ${activeTab === "about" ? "active" : ""}`}
                onClick={() => setActiveTab("about")}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                About
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "how-to-use"}
                className={`looky-tab-btn ${activeTab === "how-to-use" ? "active" : ""}`}
                onClick={() => setActiveTab("how-to-use")}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                How to use?
              </button>
            </div>
          </div>

          <button
            type="button"
            className="looky-modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content body */}
        <div className="looky-modal-body">
          {activeTab === "about" && (
            <div className="looky-tab-content fade-in">
              {/* Hero Banner */}
              <div className="looky-hero-box">
                <h3>Giving eyes to capable open-source models without vision support.</h3>
                <p>
                  Many of the smartest, most capable open-source LLMs (such as <strong>DeepSeek Coder</strong>,{" "}
                  <strong>Qwen Coder</strong>, <strong>Llama 3</strong>, and <strong>StarCoder</strong>) are exceptional software engineers,
                  yet they are text-only and lack native multimodal vision support. Coding agents running on these models cannot
                  directly inspect screenshots of UI bugs, verify CSS layout differences, read error dialogs, or analyze architecture diagrams.
                </p>
                <p>
                  <strong><span className="looky-brand-name">Looky</span> MCP</strong> bridges this gap. It acts as an intelligent visual bridge: your open-source coding agent uses <span className="looky-brand-name">Looky</span> MCP&apos;s{" "}
                  <code>describe_image</code> and <code>ocr_image</code> tools to delegate visual perception to dedicated vision-capable LLMs (such as GPT-4o,
                  Claude via OpenRouter, or local vision models). The agent receives the extracted visual intelligence and runs on that information to complete your coding task.
                </p>
                <p>
                  <strong>Supercharge usability and slash inference costs:</strong> Instead of paying premium frontier rates for an entire coding session,
                  you can rely on fast, affordable, or self-hosted open-source models for 99% of your logic and code generation, routing only occasional visual queries
                  to vision-capable endpoints when an image is present.
                </p>
              </div>

              {/* Core Features Grid */}
              <h4 className="looky-section-title">Why <span className="looky-brand-name">Looky</span> MCP?</h4>
              <div className="looky-feature-grid">
                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🚀</div>
                  <h5>Supercharge Non-Vision Models</h5>
                  <p>
                    Enable smart, text-only open-source models (DeepSeek Coder, Qwen, Llama 3) to tackle visual engineering,
                    frontend UI fixes, and diagram reasoning without switching your primary coding brain.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">💰</div>
                  <h5>Slash Inference Costs</h5>
                  <p>
                    Use inexpensive, fast, or self-hosted open-source models for 99% of your coding workflow,
                    invoking costly multimodal LLMs strictly when an image needs to be inspected.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🤝</div>
                  <h5>Best-of-Breed Intelligence Synergy</h5>
                  <p>
                    Pair models that have superior coding intellect with models that excel at visual perception,
                    bypassing the restrictions and compromises of all-in-one models.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🎯</div>
                  <h5>Tailored System Prompts</h5>
                  <p>
                    Define specialized instructions for visual bug reproduction, OCR extraction, UI/UX consistency,
                    or architecture diagram reasoning with live character counters and search.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🌐</div>
                  <h5>Universal Extra Instructions</h5>
                  <p>
                    Set global rules and behavioral guardrails once at the top of your dashboard. They are automatically
                    prepended to all vision analyses across every connected agent.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🔒</div>
                  <h5>Encrypted &amp; Privacy-First</h5>
                  <p>
                    All API keys are encrypted at rest with AES-GCM in PostgreSQL. Your images and tokens never pass
                    through third-party telemetry or cloud middlemen.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "how-to-use" && (
            <div className="looky-tab-content fade-in">
              {/* Architecture Diagram */}
              <div className="looky-architecture-card">
                <h4 className="looky-diagram-title">System Architecture &amp; Data Flow</h4>
                <div className="looky-diagram-container">
                  <svg
                    viewBox="0 0 740 180"
                    className="looky-diagram-svg"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <defs>
                      <linearGradient id="boxGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.1" />
                      </linearGradient>
                      <linearGradient id="boxGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="#059669" stopOpacity="0.1" />
                      </linearGradient>
                      <linearGradient id="boxGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="#6d28d9" stopOpacity="0.1" />
                      </linearGradient>
                      <marker
                        id="arrowhead"
                        markerWidth="8"
                        markerHeight="6"
                        refX="7"
                        refY="3"
                        orient="auto"
                      >
                        <polygon points="0 0, 8 3, 0 6" fill="#888894" />
                      </marker>
                    </defs>

                    {/* Step 1: Agent */}
                    <rect x="20" y="30" width="180" height="110" rx="12" fill="url(#boxGrad1)" stroke="#3b82f6" strokeWidth="1.5" />
                    <text x="110" y="55" textAnchor="middle" fill="currentColor" fontWeight="700" fontSize="13">Non-Vision Agent</text>
                    <text x="110" y="75" textAnchor="middle" fill="#888894" fontSize="11">DeepSeek / Qwen / Llama</text>
                    <text x="110" y="93" textAnchor="middle" fill="#888894" fontSize="11">OpenCode / Claude Code</text>
                    <rect x="35" y="105" width="150" height="24" rx="5" fill="rgba(59,130,246,0.15)" />
                    <text x="110" y="121" textAnchor="middle" fill="#60a5fa" fontSize="9.5" fontWeight="600">Delegates Vision via MCP</text>

                    {/* Arrow 1 */}
                    <path d="M 200 85 L 260 85" stroke="#888894" strokeWidth="1.8" markerEnd="url(#arrowhead)" />
                    <text x="230" y="75" textAnchor="middle" fill="#888894" fontSize="10">MCP Stdio/HTTP</text>

                    {/* Step 2: Looky MCP */}
                    <rect x="270" y="20" width="200" height="130" rx="14" fill="url(#boxGrad2)" stroke="#10b981" strokeWidth="2" />
                    <text x="370" y="50" textAnchor="middle" fill="currentColor" fontWeight="700" fontSize="15">Looky MCP Server</text>
                    <text x="370" y="70" textAnchor="middle" fill="#888894" fontSize="11">Local FastAPI + PostgreSQL</text>
                    <rect x="285" y="82" width="170" height="20" rx="5" fill="rgba(16,185,129,0.15)" />
                    <text x="370" y="96" textAnchor="middle" fill="#34d399" fontSize="10" fontWeight="600">Injects Active System Prompt</text>
                    <rect x="285" y="108" width="170" height="20" rx="5" fill="rgba(16,185,129,0.15)" />
                    <text x="370" y="122" textAnchor="middle" fill="#34d399" fontSize="10" fontWeight="600">Decrypts Profile API Key</text>

                    {/* Arrow 2 */}
                    <path d="M 470 85 L 530 85" stroke="#888894" strokeWidth="1.8" markerEnd="url(#arrowhead)" />
                    <text x="500" y="75" textAnchor="middle" fill="#888894" fontSize="10">OpenAI Vision API</text>

                    {/* Step 3: Vision Provider */}
                    <rect x="540" y="30" width="180" height="110" rx="12" fill="url(#boxGrad3)" stroke="#8b5cf6" strokeWidth="1.5" />
                    <text x="630" y="55" textAnchor="middle" fill="currentColor" fontWeight="700" fontSize="13">Vision-Capable LLM</text>
                    <text x="630" y="75" textAnchor="middle" fill="#888894" fontSize="11">OpenAI GPT-4o / Claude</text>
                    <text x="630" y="93" textAnchor="middle" fill="#888894" fontSize="11">Local Ollama / vLLM Vision</text>
                    <rect x="555" y="105" width="150" height="24" rx="5" fill="rgba(139,92,246,0.15)" />
                    <text x="630" y="121" textAnchor="middle" fill="#c084fc" fontSize="9.5" fontWeight="600">Extracts Visual Insights</text>
                  </svg>
                </div>
              </div>

              {/* Part 1: Frontend Setup */}
              <div className="looky-section-group">
                <div className="looky-section-header">
                  <span className="looky-section-badge">Part 1</span>
                  <h4>Frontend Setup (Web Dashboard)</h4>
                </div>
                <p className="looky-section-desc">
                  Configure your vision model endpoints, encrypted credentials, system instructions, and global directives from your browser.
                </p>

                <div className="looky-steps-container">
                  {/* Step 1 */}
                  <div className="looky-step-card">
                    <div className="looky-step-num">1</div>
                    <div className="looky-step-content">
                      <h5>Account Provisioning &amp; Sign In</h5>
                      <div className="looky-signup-alert">
                        <span className="alert-icon">💡</span>
                        <div className="alert-text">
                          <strong>Signup &amp; Access:</strong> Anyone can instantly sign in or sign up using <strong>Google OAuth</strong>. Email/password login remains gated and must be provisioned directly by the host admin on the server via CLI:
                          <div className="looky-code-preview" style={{ margin: "0.5rem 0" }}>
                            <div className="looky-code-header">CLI (Admin Provisioning for Email/Password)</div>
                            <pre>
                              <code>uv run python scripts/create_user.py --email you@example.com --password &apos;your-password&apos;</code>
                            </pre>
                          </div>
                        </div>
                      </div>
                      <p>
                        Once signed in via Google or provisioned by your admin, you can access the dashboard immediately.
                      </p>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="looky-step-card">
                    <div className="looky-step-num">2</div>
                    <div className="looky-step-content">
                      <h5>Configure System Prompts &amp; Universal Extra Instructions</h5>
                      <p>
                        Go to the <strong>System Prompts</strong> tab to define specialized instructions for how your vision model analyzes images (e.g. detailed UI component inspection, bug triage, or OCR text transcription). You can store up to 20 custom prompts with creation timestamps and live search.
                      </p>
                      <p>
                        Expand <strong>Universal Extra Instructions</strong> at the top of the page to define global rules (such as <em>&ldquo;Always specify exact CSS pixel discrepancies and RGB colors&rdquo;</em>) that automatically append to every prompt across all vision models.
                      </p>
                      <div className="looky-step-image-box">
                        <img
                          src={systemPromptsGuideImg}
                          alt="System Prompts and Universal Extra Instructions UI"
                          className="looky-step-image"
                          loading="lazy"
                        />
                        <div className="looky-step-image-caption">
                          <span>📸</span>
                          <span>System Prompts Dashboard — Search prompts, monitor limits, and expand Universal Extra Instructions.</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Step 3 */}
                  <div className="looky-step-card">
                    <div className="looky-step-num">3</div>
                    <div className="looky-step-content">
                      <h5>Create &amp; Activate a Vision Profile</h5>
                      <p>
                        Navigate to <strong>Vision Profiles</strong> to configure your vision model endpoints (supporting up to 30 profiles). Click <em>New Vision Profile</em> and provide:
                      </p>
                      <ul className="looky-step-list">
                        <li><strong>Provider / Name</strong>: e.g. <code>GPT-4o Vision</code> or <code>Local Qwen2-VL</code></li>
                        <li><strong>Base URL</strong>: <code>https://api.openai.com/v1</code> or <code>http://localhost:11434/v1</code></li>
                        <li><strong>Model Name</strong>: e.g. <code>gpt-4o</code>, <code>claude-3-5-sonnet-20241022</code></li>
                        <li><strong>API Key</strong>: Your encrypted API key (or dummy token for local endpoints)</li>
                        <li><strong>Linked Prompt</strong>: Select your preferred default system prompt preset</li>
                      </ul>
                      <p>
                        Click <strong>Activate</strong> on your desired profile. <span className="looky-brand-name">Looky</span> MCP will immediately route all incoming agent queries to this active profile.
                      </p>
                      <div className="looky-step-image-box">
                        <img
                          src={visionProfilesGuideImg}
                          alt="Vision Profiles Management UI"
                          className="looky-step-image"
                          loading="lazy"
                        />
                        <div className="looky-step-image-caption">
                          <span>📸</span>
                          <span>Vision Profiles Manager — Manage endpoints, encrypted API keys, and instantly toggle active models.</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Part 2: CLI & Agent Integration */}
              <div className="looky-section-group">
                <div className="looky-section-header">
                  <span className="looky-section-badge">Part 2</span>
                  <h4>CLI &amp; Coding Agent Setup</h4>
                </div>
                <p className="looky-section-desc">
                  Connect your text-only coding agent (DeepSeek Coder, Qwen Coder, Llama 3 via Claude Code CLI, OpenCode, or Cursor) to <span className="looky-brand-name">Looky</span> MCP.
                </p>

                <div className="looky-steps-container">
                  {/* Step 4 */}
                  <div className="looky-step-card">
                    <div className="looky-step-num">4</div>
                    <div className="looky-step-content">
                      <h5>Connect Your Agent via MCP Protocol</h5>
                      <p>
                        Switch to the <strong>MCP Access</strong> tab in the web dashboard. <span className="looky-brand-name">Looky</span> MCP displays your persistent gateway URL, personal access token, and one-click copyable configuration snippets.
                      </p>
                      <div className="looky-step-image-box">
                        <img
                          src={mcpAccessGuideImg}
                          alt="MCP Access Tab and CLI Commands"
                          className="looky-step-image"
                          loading="lazy"
                        />
                        <div className="looky-step-image-caption">
                          <span>📸</span>
                          <span>MCP Access Tab — Instant copyable CLI setup commands and authorization Bearer headers.</span>
                        </div>
                      </div>
                      <div className="looky-code-preview">
                        <div className="looky-code-header">Terminal (Claude Code CLI)</div>
                        <pre>
                          <code>
                            claude mcp add --transport http looky-mcp http://localhost:8000/mcp \<br />
                            {"  "}--header &quot;Authorization: Bearer YOUR_MCP_KEY&quot;
                          </code>
                        </pre>
                      </div>
                      <p className="looky-code-note">
                        For OpenCode, Cursor, or Windsurf, paste the JSON snippet provided in <em>MCP Access</em> directly into your editor&apos;s MCP config file.
                      </p>
                    </div>
                  </div>

                  {/* Step 5 */}
                  <div className="looky-step-card">
                    <div className="looky-step-num">5</div>
                    <div className="looky-step-content">
                      <h5>Supercharge Your Non-Vision Agent!</h5>
                      <p>
                        Now ask your coding agent to inspect an image or UI error. Even if your agent runs on a text-only
                        open-source model (like <strong>DeepSeek Coder</strong>, <strong>Qwen</strong>, or <strong>Llama 3</strong>), it autonomously calls
                        <span className="looky-brand-name"> Looky</span> MCP&apos;s <code>describe_image</code> tool:
                      </p>
                      <div className="looky-prompt-quote">
                        &ldquo;Look at frontend/src/assets/bug-screenshot.png and fix the misalignment in the navbar.&rdquo;
                      </div>
                      <p>
                        <span className="looky-brand-name">Looky</span> MCP forwards the image to your configured vision LLM, extracts the visual layout discrepancies,
                        and feeds the insight straight back to your open-source model to write the fix!
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* FAQs Section */}
              <h4 className="looky-section-title">Frequently Asked Questions (FAQs)</h4>
              <div className="looky-faqs-grid">
                <div className="looky-faq-card looky-faq-highlight">
                  <h6>Why use <span className="looky-brand-name">Looky</span> MCP instead of directly using a multimodal LLM for all coding?</h6>
                  <p>
                    Specialized open-source models (such as DeepSeek Coder or Qwen Coder) often surpass general multimodal LLMs
                    at deep code refactoring, complex logic, and repository reasoning, but are completely text-only. Meanwhile,
                    multimodal models (like GPT-4o) are expensive and rate-limited. <span className="looky-brand-name">Looky</span> MCP decouples coding intelligence from vision:
                    you run 99% of your workflow on cheap, fast, or self-hosted open-source models and borrow vision capabilities
                    strictly when an image needs to be inspected.
                  </p>
                </div>

                <div className="looky-faq-card looky-faq-highlight">
                  <h6>How does the signup / account creation process work?</h6>
                  <p>
                    Anyone can sign in or create an account instantly using <strong>Google OAuth</strong>.
                    For email and password access, accounts remain gated and are provisioned directly on the server by running <code>uv run python scripts/create_user.py --email &lt;email&gt; --password &apos;&lt;pwd&gt;&apos;</code>.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>Which vision models and providers are supported?</h6>
                  <p>
                    Any endpoint supporting the standard OpenAI Chat Completions vision payload format. This includes OpenAI
                    (GPT-4o, GPT-4o-mini), OpenRouter, Groq, or self-hosted models running on Ollama, vLLM, or LM Studio.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>What MCP tools does <span className="looky-brand-name">Looky</span> MCP expose to coding agents?</h6>
                  <p>
                    <span className="looky-brand-name">Looky</span> MCP provides two standard tools: <code>describe_image</code> (for contextual visual questions,
                    bug reproduction, diagram reasoning) and <code>ocr_image</code> (specifically optimized for high-fidelity text extraction).
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>Where are my vision model API keys stored?</h6>
                  <p>
                    All API keys are encrypted at rest in your local PostgreSQL database using AES-GCM encryption with an
                    isolated application secret. They are never written to unencrypted logs or exposed in API responses.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>Can I switch models without restarting my coding agent?</h6>
                  <p>
                    Yes! That is one of <span className="looky-brand-name">Looky</span> MCP&apos;s primary superpowers. Your coding agent always connects to the same
                    MCP gateway URL. When you activate a different Vision Profile in the web dashboard, the very next image
                    query routes to your new model seamlessly.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>Can I run this fully offline with local hardware?</h6>
                  <p>
                    Yes. Point your Vision Profile Base URL to your local Ollama or vLLM instance (e.g. <code>http://localhost:11434/v1</code>)
                    with a vision-capable model like Llama 3.2 Vision, MiniCPM-V, or Qwen2-VL. No data leaves your machine.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>How do Universal Extra Instructions work?</h6>
                  <p>
                    Universal Extra Instructions are global rules (such as &ldquo;Always note CSS padding discrepancies&rdquo; or
                    &ldquo;List exact RGB hex values if colors differ&rdquo;) that automatically concatenate onto every vision query,
                    ensuring uniform standards across all profiles.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
