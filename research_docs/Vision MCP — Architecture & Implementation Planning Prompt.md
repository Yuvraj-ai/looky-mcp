# Vision MCP — Architecture & Implementation Planning

You are working on a project called **Vision MCP**, a lightweight visual-perception MCP server designed to work with OpenCode.

I have already completed the requirements/decision phase. The attached Markdown files contain the authoritative decisions for the project.

## IMPORTANT: READ THE MARKDOWN FILES FIRST

Before proposing anything, locate and read all of these project decision documents:

- `vision_mcp_decisions_1_to_3.md`
- `vision_mcp_decisions_4_to_6.md`
- `vision_mcp_decisions_7_to_9.md`
- `vision_mcp_decision_10.md`

If the filenames differ slightly, locate the corresponding files by their contents.

Treat these documents as the **source of truth**.

Do not override, reinterpret, or silently change anything marked as **LOCKED**.

If two documents appear inconsistent, stop and explicitly identify the conflict rather than guessing.

---

# YOUR TASK

We are now moving from:

> Requirements / Decisions

to:

> Architecture & Implementation Design

Do **NOT** start writing the application yet.

First produce a complete, practical architecture and implementation plan based on the locked requirements.

The goal is to determine:

1. overall system architecture
2. backend architecture
3. frontend architecture
4. database schema
5. API design
6. MCP implementation
7. authentication architecture
8. Vision LLM integration
9. project directory structure
10. security boundaries
11. request/data flows
12. implementation order

The architecture should be **simple, production-oriented, and appropriate for a low-spec server**.

---

# CORE PROJECT PHILOSOPHY

Follow this rule throughout the design:

> **Do we actually need this for the requirements?**

If something is not required, do not introduce it just because it is a popular technology or considered "best practice."

Avoid unnecessary complexity.

Do NOT introduce:

- LangGraph
- RAG
- vector databases
- autonomous agents
- agent orchestration
- Redis
- Kafka
- Celery
- RabbitMQ
- microservices
- Kubernetes
- event buses
- unnecessary caching layers
- unnecessary abstraction frameworks
- provider-specific SDK integrations
- complicated frontend state-management systems

unless you can demonstrate that a locked requirement actually requires them.

If something could reasonably be useful later but is not required now, mark it as:

> DEFERRED

rather than implementing it.

---

# LOCKED HIGH-LEVEL REQUIREMENTS

Use the Markdown documents for the complete details, but these are the most important constraints.

## Backend

- Python
- ASGI application
- normal authenticated API
- MCP endpoint
- same backend application hosts both
- low-resource deployment is important

## Frontend

- TypeScript
- authenticated frontend
- UI for managing users' configuration/resources

## Database

A persistent relational database is required.

Current direction is PostgreSQL, but verify whether the architecture should lock PostgreSQL now or whether the DB choice should remain an implementation decision.

The database must support at least:

- users
- system prompts
- vision profiles
- MCP credentials

All user-owned resources must be scoped to the authenticated user's UUID.

Never trust a caller-provided user ID as the basis for authorization.

---

# AUTHENTICATION

There are two distinct authentication contexts.

## Frontend authentication

The application should support:

- Google OAuth if practical
- email/password authentication
- no public signup

Users are provisioned through an administrative/script mechanism.

## MCP authentication

MCP uses a dedicated API key.

The MCP key is separate from frontend login/session credentials.

OpenCode sends:

```http
Authorization: Bearer <MCP_API_KEY>
```

The backend maps the MCP key to a user UUID.

One MCP key per user initially.

Only the hash is stored in the database.

Plaintext key is shown to the user once after generation.

Regenerating the key revokes the old key.

No MCP OAuth in v1.

---

# MCP TRANSPORT

Use:

> Remote MCP over Streamable HTTP

Endpoint:

```text
/mcp
```

Example:

```text
https://your-domain.com/mcp
```

Do not use SSE as the primary transport.

Do not use stdio for the deployed architecture.

Use the official Python MCP SDK.

The MCP server should be integrated into the same ASGI application as the normal API.

Origin validation must be handled appropriately for Streamable HTTP.

---

# MCP TOOLS

Exactly two MCP tools exist:

```text
describe_image(image, prompt)
ocr_image(image, prompt)
```

The primary LLM chooses the operation.

The primary LLM must NOT choose:

- user ID
- Vision Profile
- model
- endpoint
- API key

The backend determines all of those from the authenticated MCP identity and the user's active Vision Profile.

---

# VISION PROFILES

Each user has Vision Profiles.

A Vision Profile contains conceptually:

```text
id
user_id
name
endpoint
model
system_prompt_id
encrypted_api_key
is_active
created_at
updated_at
```

Only one Vision Profile is active per user.

The frontend allows the user to create/edit/delete/manage profiles.

API keys must be encrypted at rest.

The encryption master key must NOT be stored in the database.

Never return decrypted API keys to the frontend.

The frontend may receive metadata such as:

```text
has_api_key: true
```

API keys should only be decrypted temporarily in memory when making the Vision request.

Only OpenAI-compatible Vision endpoints are supported in v1.

No arbitrary advanced model parameters initially.

---

# SYSTEM PROMPTS

There is a frontend page called:

> System Prompts

Users can:

- create
- edit
- delete
- manage

their System Prompts.

Each prompt has:

```text
id
user_id
title
content
created_at
updated_at
```

Vision Profiles reference System Prompts by UUID.

System prompt contents should not be duplicated inside Vision Profiles.

Authorization must prevent one user from accessing another user's prompts.

You must determine appropriate deletion behavior when a System Prompt is referenced by a Vision Profile.

Do not silently choose destructive behavior.

Recommend the simplest safe solution and explain it.

---

# VISION MODES

There are exactly two operations.

## Image Description

Flow:

```text
System Prompt
+
Universal Extra Instructions
+
User Prompt
+
Image
↓
Vision LLM
↓
Result
```

## OCR

Flow:

```text
System Prompt
+
User Prompt
+
Image
↓
Vision LLM
↓
Result
```

The universal Extra Instructions are used ONLY for Image Description.

They are NOT used for OCR.

The backend determines this based on which MCP tool was called.

---

# IMAGE HANDLING

MCP uses:

```text
ImageContent
```

with:

```text
type = "image"
data = base64 encoded image
mimeType = image MIME type
```

Limits:

- maximum encoded image size: 5 MB
- maximum resolution: approximately 8.3 megapixels

Supported:

- JPEG/JPG
- PNG
- WebP

Unsupported:

- GIF
- BMP
- TIFF
- SVG

The backend must:

1. validate base64
2. verify actual image format
3. verify supported format
4. attempt decoding
5. reject corrupted images
6. enforce size limit
7. enforce pixel-count limit

Do not:

- resize
- compress
- crop
- convert format

Images should not be unnecessarily persisted.

---

# RATE LIMITING

Per authenticated user:

```text
20 vision calls per rolling 60 seconds
3 concurrent vision calls
```

Applies to both MCP tools.

Limits are checked before calling the Vision provider.

If a limit is reached:

- reject immediately
- do not queue
- do not retry
- do not call the provider

v1 uses in-memory rate/concurrency state.

Do not introduce Redis just for this.

The architecture must document the limitation that in-memory state is per application process.

---

# ERROR HANDLING

Failures should be immediate.

No automatic retries.

No provider fallback.

Examples of stable errors:

```text
Image data is invalid
Image format is unsupported
Image exceeds size limit
Image resolution exceeds limit
No active Vision Profile is configured
Vision Profile authentication failed
Vision service temporarily unavailable
Vision request timed out
Vision call rate limit reached
Too many concurrent vision calls
Vision service returned invalid response
```

Do not expose:

- API keys
- DB credentials
- stack traces
- internal filesystem paths
- unnecessary provider internals

Determine the cleanest implementation for application-level errors and MCP errors.

---

# VISION LLM REQUEST

Use LangChain narrowly.

The intended conceptual interface is:

```text
ChatOpenAI(
    model = profile.model,
    api_key = decrypted_api_key,
    base_url = profile.endpoint,
    timeout = 60,
    max_retries = 0
)
```

Do not turn LangChain into an agent framework.

LangChain's responsibility is primarily:

```text
construct request
→ send multimodal request
→ receive response
→ expose response
```

Our backend remains responsible for:

- authentication
- authorization
- selecting active Vision Profile
- image validation
- rate limiting
- concurrency
- error translation
- database access
- request lifecycle

Locked:

```text
timeout = 60 seconds
max_retries = 0
```

No Vision LLM streaming in v1.

Return the useful textual model response to MCP.

Do not expose raw provider responses.

No provider fallback.

---

# OPEN CODE

OpenCode connects remotely using Streamable HTTP.

The recommended configuration uses an environment variable:

```text
VISION_MCP_KEY=...
```

and:

```json
{
  "mcp": {
    "vision": {
      "type": "remote",
      "url": "https://your-server.com/mcp",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:VISION_MCP_KEY}"
      }
    }
  }
}
```

The frontend should eventually be able to provide a ready-to-copy OpenCode configuration snippet.

Do not make storing the plaintext key directly in `opencode.json` the recommended approach.

---

# WHAT I WANT FROM YOU NOW

Do not code yet.

Produce the architecture/design document in the following order.

## 1. Architecture Overview

Explain the complete system in simple language.

Show the major components:

```text
Frontend
Backend
Database
MCP
Vision LLM provider
OpenCode
```

Explain how they communicate.

Provide an architecture diagram.

---

## 2. Component Responsibilities

For every major component, explain:

- what it does
- what it owns
- what it must NOT do
- what it communicates with

For example:

```text
Frontend
    ↓
Backend API
    ↓
Database
```

and:

```text
OpenCode
    ↓
MCP
    ↓
Vision service
    ↓
Vision LLM
```

Keep responsibilities clean.

---

# 3. Backend Framework Decision

Recommend the backend framework.

Likely candidates include:

- FastAPI
- Starlette
- another appropriate ASGI framework

Research current compatibility with:

- Python MCP SDK
- Streamable HTTP
- MCP mounting/integration
- authentication middleware
- async execution

Choose the simplest suitable option.

Explain why.

Do not choose a framework merely because it is popular.

---

# 4. Frontend Stack Decision

Recommend a practical TypeScript frontend stack.

Consider simplicity and low development overhead.

Do not introduce unnecessary libraries.

Explain:

- framework
- routing
- API communication
- authentication handling
- state management
- UI approach

Keep it lightweight.

---

# 5. Database Decision

Recommend the relational database.

PostgreSQL is currently favored, but verify whether it is the right choice.

Design the initial schema.

At minimum consider:

```text
users
system_prompts
vision_profiles
mcp_credentials
```

Show:

- columns
- data types
- primary keys
- foreign keys
- indexes
- uniqueness constraints
- timestamps
- ownership relationships

Explain important authorization boundaries.

---

# 6. System Prompt Deletion Semantics

A Vision Profile references a System Prompt.

Determine what should happen if the user attempts to delete a referenced System Prompt.

Prefer the simplest safe behavior.

Possible approaches:

```text
RESTRICT
SET NULL
CASCADE
```

Do not automatically choose one without reasoning.

Explain the recommendation.

---

# 7. Vision Profile Data Model

Design the complete Vision Profile schema.

Include:

- encrypted API key
- active profile constraint
- System Prompt relationship
- user ownership
- timestamps

Determine how to enforce:

> Only one active Vision Profile per user.

Prefer database-level protection where practical.

---

# 8. MCP Credential Model

Design the MCP credential table.

Consider:

```text
id
user_id
key_hash
created_at
updated_at
revoked_at
```

Determine whether we actually need fields such as:

```text
last_used_at
```

Do not add them automatically.

Explain what is necessary versus optional.

---

# 9. Authentication Architecture

Design frontend authentication.

Cover:

- email/password
- Google OAuth
- sessions/tokens
- password hashing
- authentication middleware
- user provisioning
- no public signup

Then separately design:

```text
MCP API key authentication
```

Explain exactly how:

```text
Authorization: Bearer ...
        ↓
hash/verify
        ↓
user UUID
        ↓
request context
```

works.

Do not mix frontend session authentication and MCP API-key authentication.

---

# 10. Authorization Model

Define the authorization rule clearly:

```text
authenticated identity
        ↓
user UUID
        ↓
only resources owned by that UUID
```

Show how this applies to:

- System Prompts
- Vision Profiles
- MCP credentials
- API requests

Explain how cross-user access is prevented.

---

# 11. API Design

Design the normal backend API.

For example:

```text
/api/auth/...
/api/system-prompts/...
/api/vision-profiles/...
/api/mcp/...
```

Determine the exact routes needed.

For every endpoint specify:

- HTTP method
- path
- purpose
- authentication requirement
- request body
- response shape
- authorization rule
- important errors

Do not create endpoints that aren't needed.

---

# 12. MCP API / Tool Design

Design the `/mcp` endpoint and the two tools:

```text
describe_image
ocr_image
```

Define:

- tool name
- tool description
- arguments
- image representation
- prompt
- what the tool returns
- authentication
- errors

Ensure tool arguments do NOT allow the caller to specify:

```text
user_id
profile_id
model
endpoint
api_key
```

---

# 13. Request Lifecycle

Give the complete lifecycle for:

## describe_image

```text
OpenCode
↓
MCP authentication
↓
user identity
↓
rate limit
↓
concurrency
↓
active Vision Profile
↓
System Prompt
↓
image validation
↓
build request
↓
Vision LLM
↓
response
↓
MCP
↓
OpenCode
```

Explain every stage.

Then do the same for OCR.

---

# 14. Concurrency Implementation

Determine the simplest correct implementation for:

```text
3 concurrent vision calls per user
```

Explain:

- how active count is tracked
- how it is incremented
- how it is decremented
- how failures/timeouts release the slot
- how race conditions are avoided

Keep it lightweight.

Do not introduce Redis.

---

# 15. Rate Limiter Implementation

Determine the simplest suitable in-memory implementation for:

```text
20 calls / rolling 60 seconds / user
```

Explain:

- data structure
- cleanup
- locking/concurrency safety
- memory behavior
- behavior after process restart
- behavior with multiple worker processes

Do not overengineer it.

---

# 16. Vision Service Layer

Design a clean backend service abstraction.

Something conceptually like:

```text
MCP layer
    ↓
VisionService
    ↓
VisionProfileRepository
    ↓
LangChain/OpenAI-compatible model
```

Determine whether a dedicated service abstraction is useful.

Avoid unnecessary layers.

The key requirement is that MCP tool code should not become a giant block containing:

- authentication
- DB logic
- image validation
- rate limiting
- LangChain
- error translation

But also avoid creating dozens of tiny abstractions.

Find the reasonable middle ground.

---

# 17. Image Validation Layer

Design where image validation should live.

Determine:

- base64 validation
- MIME validation
- actual file signature validation
- decoding
- pixel-count validation
- size validation

Identify a suitable Python image library.

Do not resize or transform images.

Explain memory considerations for 8.3 MP images.

---

# 18. Vision LLM Integration

Design the Vision LLM integration.

Show how:

```text
Vision Profile
↓
endpoint
model
encrypted API key
System Prompt
↓
decrypt key
↓
ChatOpenAI
↓
multimodal request
```

works.

Show the conceptual request structure for:

### Description

```text
system
user text
extra instructions
image
```

### OCR

```text
system
user text
image
```

Make sure Extra Instructions never accidentally enter OCR.

---

# 19. Timeout & Error Architecture

Explain how the 60-second timeout is enforced.

Explain how provider exceptions become stable application errors.

Do not leak sensitive information.

Determine where error translation should occur.

---

# 20. Security Architecture

Perform a practical security review.

Cover:

- password hashing
- OAuth
- session/token security
- MCP API key hashing
- API key encryption
- encryption master key
- HTTPS
- CORS
- CSRF where applicable
- Origin validation for MCP
- SQL injection protection
- authorization
- request validation
- logging
- secret leakage
- image memory handling
- rate limiting
- concurrency abuse
- error leakage

Do not turn this into an enterprise security architecture.

Focus on realistic risks for this application.

---

# 21. Project Directory Structure

Propose the complete repository structure.

For example:

```text
project/
├── backend/
├── frontend/
├── scripts/
├── docs/
└── ...
```

Then show meaningful backend directories/files.

Do not create folders merely because they are conventional.

Every major directory should have a reason.

---

# 22. Configuration & Environment Variables

Define all environment variables needed.

For example:

```text
DATABASE_URL
APP_SECRET_KEY
VISION_ENCRYPTION_KEY
...
```

Determine what belongs in:

- environment variables
- database
- source code/config

Never store secrets in source control.

Also distinguish:

```text
application secrets
```

from:

```text
user Vision Profile API keys
```

---

# 23. Deployment Architecture

Design a simple low-resource deployment.

Target:

```text
one application server
+
PostgreSQL
```

Explain:

- backend process
- frontend serving/deployment
- reverse proxy if required
- HTTPS
- database connection
- environment secrets

Do not introduce Docker/Kubernetes/Redis unless there is a clear requirement.

If Docker is useful but optional, mark it as optional rather than mandatory.

---

# 24. Development Environment

Explain how the application should be run locally.

Include:

```text
backend
frontend
database
```

and local MCP testing.

Do not require production infrastructure just to develop the application.

---

# 25. Implementation Order

Give a staged implementation plan.

For example:

```text
Phase 1 — project skeleton
Phase 2 — database
Phase 3 — authentication
Phase 4 — System Prompts
Phase 5 — Vision Profiles
Phase 6 — MCP authentication
Phase 7 — MCP endpoint
Phase 8 — image validation
Phase 9 — Vision LLM service
Phase 10 — rate/concurrency limits
Phase 11 — frontend integration
Phase 12 — testing
Phase 13 — deployment
```

But determine the actual order based on dependencies.

---

# 26. Testing Strategy

Design a practical test strategy.

Cover at minimum:

### Authentication

- valid login
- invalid login
- unauthorized access
- cross-user access

### System Prompts

- CRUD
- ownership
- deletion while referenced

### Vision Profiles

- CRUD
- API key encryption
- active profile behavior
- one active profile

### MCP

- valid MCP key
- invalid MCP key
- revoked MCP key
- correct user identity

### Image validation

- valid JPEG
- valid PNG
- valid WebP
- invalid base64
- corrupted image
- unsupported format
- >5 MB
- >8.3 MP

### Rate limiting

- 20 allowed
- 21st rejected
- rolling-window behavior

### Concurrency

- 3 allowed
- 4th rejected
- slot released after success
- slot released after failure
- slot released after timeout

### Vision service

- successful request
- provider authentication failure
- provider timeout
- provider 429
- provider 5xx
- malformed response

---

# 27. Locked vs Deferred

At the end, create a table:

| Item | Status | Reason |
|---|---|---|
| ... | LOCKED | ... |
| ... | IMPLEMENTATION DETAIL | ... |
| ... | DEFERRED | ... |

Do not accidentally convert implementation details into new product decisions.

The goal is to minimize future decision churn.

---

# 28. Identify Genuine Unknowns

After completing the architecture, list only things that genuinely cannot be determined from the requirements.

For each unknown:

```text
Question
Why it matters
Possible options
Recommended option
Whether it must be decided before coding
```

Do not invent questions just to make the list longer.

If there are no meaningful blockers, say so.

---

# 29. Final Architecture Summary

End with a concise final architecture diagram such as:

```text
                         ┌───────────────────┐
                         │     OpenCode      │
                         └─────────┬─────────┘
                                   │
                         MCP / HTTPS / Bearer
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────┐
│                  Python ASGI Backend                     │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │ Normal API   │    │ MCP /mcp     │                   │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                    │                           │
│         └──────────┬─────────┘                           │
│                    ▼                                     │
│            Authentication / AuthZ                        │
│                    │                                     │
│          ┌─────────┴──────────┐                          │
│          │                    │                          │
│     PostgreSQL          Vision Service                  │
│                               │                          │
│                        LangChain                        │
│                               │                          │
└───────────────────────────────┼──────────────────────────┘
                                │
                                ▼
                       Vision LLM Provider
```

Then summarize the recommended technology stack.

---

# VERY IMPORTANT IMPLEMENTATION RULES

1. **Do not code yet.**
2. Read all Markdown decision files before designing.
3. Locked decisions are authoritative.
4. Do not add technology without a requirement-driven reason.
5. Prefer simple solutions.
6. Prefer a modular monolith over microservices.
7. Keep the low-resource deployment requirement in mind.
8. Do not add Redis.
9. Do not add LangGraph.
10. Do not add RAG/vector databases.
11. Do not add autonomous agents.
12. Do not add provider-specific integrations in v1.
13. Do not add streaming.
14. Do not add automatic retries.
15. Do not allow the primary LLM to select Vision Profiles.
16. Do not trust caller-supplied user IDs.
17. Do not expose secrets in API responses or logs.
18. Do not store decrypted Vision API keys in the database.
19. Do not store MCP API keys in plaintext.
20. Do not change locked image limits.
21. Do not resize or transform incoming images.
22. Do not silently change OCR or Image Description behavior.
23. Do not implement features simply because they may be useful later.
24. If something is not required, defer it.

---

# EXPECTED OUTPUT

Your output should be a **complete architecture/design proposal**, not code.

Structure it with clear headings.

Use diagrams and tables where useful.

For every major technology choice, explain:

> Why this is needed for our requirements.

and:

> Why we are NOT choosing the more complicated alternatives.

At the end, clearly state:

1. **Architecture recommended**
2. **Technology stack recommended**
3. **Database schema**
4. **API structure**
5. **MCP structure**
6. **Project structure**
7. **Implementation sequence**
8. **Remaining genuine decisions/blockers**

Only after this architecture is reviewed and approved should implementation begin.