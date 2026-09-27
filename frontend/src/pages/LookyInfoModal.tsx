import { useEffect, useState } from "react";

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
              <h2 id="looky-modal-title">Looky MCP</h2>
            </div>
            <span className="looky-modal-tagline">Self-Hosted Vision for AI Coding Agents</span>
          </div>

          <div className="looky-modal-header-right">
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
        </div>

        {/* Content body */}
        <div className="looky-modal-body">
          {activeTab === "about" && (
            <div className="looky-tab-content fade-in">
              {/* Hero Banner */}
              <div className="looky-hero-box">
                <h3>Coding agents can&apos;t see. Looky MCP gives them eyes.</h3>
                <p>
                  Leading AI coding agents like <strong>Claude Code</strong>, <strong>OpenCode</strong>,{" "}
                  <strong>Cursor</strong>, and <strong>Cline</strong> excel at writing and refactoring code, but they
                  are text-bound. When you share a screenshot of an error dialog, a Figma UI mockup, or a complex
                  database ER diagram, they are blind to the pixels.
                </p>
                <p>
                  <strong>Looky MCP</strong> bridges this gap. It operates as a self-hosted{" "}
                  <strong>Model Context Protocol (MCP)</strong> server that exposes <code>describe_image</code> and{" "}
                  <code>ocr_image</code> tools directly to your coding assistant, routing queries through your own
                  configured vision LLM.
                </p>
              </div>

              {/* Core Features Grid */}
              <h4 className="looky-section-title">Why Looky MCP?</h4>
              <div className="looky-feature-grid">
                <div className="looky-feature-card">
                  <div className="looky-feature-icon">👁️</div>
                  <h5>Bring Your Own Vision Model</h5>
                  <p>
                    Use any OpenAI-compatible vision endpoint: OpenAI (GPT-4o, GPT-4o-mini), Anthropic via OpenRouter,
                    Groq, or run completely private local vision models via vLLM or Ollama.
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

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">⚡</div>
                  <h5>Zero-Touch Model Switching</h5>
                  <p>
                    Activate a new vision profile in the web app and all connected agents immediately use the new model
                    and prompt without restarting your terminal or touching configuration files.
                  </p>
                </div>

                <div className="looky-feature-card">
                  <div className="looky-feature-icon">🛡️</div>
                  <h5>Protection &amp; Limits</h5>
                  <p>
                    Built-in concurrency and rate limiters safeguard your budget from rogue runaway agent loops,
                    with up to 20 custom system prompts and 30 active vision profiles.
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
                    <text x="110" y="60" textAnchor="middle" fill="currentColor" fontWeight="700" fontSize="14">AI Coding Agent</text>
                    <text x="110" y="80" textAnchor="middle" fill="#888894" fontSize="11">Claude Code / OpenCode</text>
                    <text x="110" y="98" textAnchor="middle" fill="#888894" fontSize="11">Cursor / Windsurf</text>
                    <rect x="35" y="110" width="150" height="20" rx="5" fill="rgba(59,130,246,0.15)" />
                    <text x="110" y="124" textAnchor="middle" fill="#60a5fa" fontSize="10" fontWeight="600">Calls describe_image</text>

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
                    <text x="630" y="60" textAnchor="middle" fill="currentColor" fontWeight="700" fontSize="14">Vision Model</text>
                    <text x="630" y="80" textAnchor="middle" fill="#888894" fontSize="11">OpenAI GPT-4o</text>
                    <text x="630" y="98" textAnchor="middle" fill="#888894" fontSize="11">OpenRouter / Groq</text>
                    <rect x="555" y="110" width="150" height="20" rx="5" fill="rgba(139,92,246,0.15)" />
                    <text x="630" y="124" textAnchor="middle" fill="#c084fc" fontSize="10" fontWeight="600">Local Ollama / vLLM</text>
                  </svg>
                </div>
              </div>

              {/* Step by Step Guide */}
              <h4 className="looky-section-title">Step-by-Step Setup Guide</h4>
              <div className="looky-steps-container">
                {/* Step 1 */}
                <div className="looky-step-card">
                  <div className="looky-step-num">1</div>
                  <div className="looky-step-content">
                    <h5>Sign In &amp; Configure System Prompts</h5>
                    <p>
                      Log into Looky MCP. Go to <strong>System Prompts</strong> to craft instructions for how your
                      vision model should extract UI, identify bugs, or read text. Expand{" "}
                      <strong>Universal Extra Instructions</strong> to apply global directives across every prompt.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="looky-step-card">
                  <div className="looky-step-num">2</div>
                  <div className="looky-step-content">
                    <h5>Create &amp; Activate a Vision Profile</h5>
                    <p>
                      Navigate to <strong>Vision Profiles</strong> and click <em>New Vision Profile</em>. Enter:
                    </p>
                    <ul className="looky-step-list">
                      <li><strong>Provider / Name</strong>: e.g. <code>GPT-4o Vision</code> or <code>Local Qwen2-VL</code></li>
                      <li><strong>Base URL</strong>: <code>https://api.openai.com/v1</code> or <code>http://localhost:11434/v1</code></li>
                      <li><strong>Model Name</strong>: e.g. <code>gpt-4o</code>, <code>claude-3-5-sonnet-20241022</code></li>
                      <li><strong>API Key</strong>: Your encrypted API key (or dummy token for local endpoints)</li>
                      <li><strong>Linked Prompt</strong>: Select your preferred system prompt preset</li>
                    </ul>
                    <p>Click <strong>Activate</strong> so Looky MCP knows which endpoint to route requests to.</p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="looky-step-card">
                  <div className="looky-step-num">3</div>
                  <div className="looky-step-content">
                    <h5>Connect Claude Code or OpenCode via CLI</h5>
                    <p>
                      Switch to the <strong>MCP Access</strong> tab and copy your generated MCP command or configuration snippet.
                    </p>
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
                      Or for OpenCode / Cursor, paste the JSON snippet provided in <em>MCP Access</em> directly into your project config.
                    </p>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="looky-step-card">
                  <div className="looky-step-num">4</div>
                  <div className="looky-step-content">
                    <h5>Ask Your Agent to See!</h5>
                    <p>
                      Now simply ask your coding agent to inspect an image or UI error. For example:
                    </p>
                    <div className="looky-prompt-quote">
                      &ldquo;Look at frontend/src/assets/bug-screenshot.png and fix the misalignment in the navbar.&rdquo;
                    </div>
                    <p>
                      The agent autonomously invokes Looky MCP&apos;s <code>describe_image</code> tool, receives accurate visual
                      analysis, and writes the code fix for you!
                    </p>
                  </div>
                </div>
              </div>

              {/* FAQs Section */}
              <h4 className="looky-section-title">Frequently Asked Questions (FAQs)</h4>
              <div className="looky-faqs-grid">
                <div className="looky-faq-card">
                  <h6>Which vision models and providers are supported?</h6>
                  <p>
                    Any endpoint supporting the standard OpenAI Chat Completions vision payload format. This includes OpenAI
                    (GPT-4o, GPT-4o-mini), OpenRouter, Groq, or self-hosted models running on Ollama, vLLM, or LM Studio.
                  </p>
                </div>

                <div className="looky-faq-card">
                  <h6>What MCP tools does Looky MCP expose to coding agents?</h6>
                  <p>
                    Looky MCP provides two standard tools: <code>describe_image</code> (for contextual visual questions,
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
                    Yes! That is one of Looky MCP&apos;s primary superpowers. Your coding agent always connects to the same
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
