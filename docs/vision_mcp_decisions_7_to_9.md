# Vision MCP Project — Decisions #7–#9

## Status

- Decision #7 — MCP Key Provisioning & OpenCode Configuration: **LOCKED**
- Decision #8 — MCP Endpoint & Transport Architecture: **LOCKED**
- Decision #9 — Rate Limiting & Concurrency: **LOCKED**

This document consolidates the decisions, reasoning, assumptions, flows, and deferred items for the lightweight Vision MCP project.

---

# 1. Project Context

The project is a lightweight Python backend + TypeScript frontend application that provides a vision sidecar/gateway for OpenCode.

OpenCode's primary LLM may not support vision. Instead of changing the primary model, OpenCode can call:

```text
describe_image(image, prompt)
ocr_image(image, prompt)
```

The MCP server authenticates the user, identifies that user's active Vision Profile, sends the image and instructions to the configured OpenAI-compatible vision model, and returns the result.

The user chooses the active Vision Profile. The primary LLM does not choose the vision model/profile.

The project is intentionally designed to remain simple and lightweight enough for low-spec deployments.

---

# 2. Relevant Previously Locked Context

## Authentication

MCP uses a dedicated MCP API key/token, separate from frontend login/session authentication.

OpenCode sends:

```http
Authorization: Bearer <MCP_API_KEY>
```

The backend maps the credential to a user UUID.

MCP tool arguments do not contain trusted:

- user_id
- profile_id
- model
- endpoint
- API key

## Vision Profiles

Initially, each user has one active Vision Profile.

Conceptually:

```text
name
endpoint
model
system_prompt_id
encrypted_api_key
is_active
```

Vision provider support is currently limited to OpenAI-compatible endpoints.

## MCP Tools

Exactly two tools:

```text
describe_image(image, prompt)
ocr_image(image, prompt)
```

The primary LLM chooses the operation, but not the profile/model.

## Image Transmission

MCP `ImageContent` is used:

```text
type = "image"
data = base64-encoded image
mimeType = image MIME type
```

## Image Limits

Locked limits:

- Maximum encoded image size: 5 MB
- Maximum resolution: approximately 8.3 megapixels
- JPEG/JPG, PNG, WebP supported
- GIF, BMP, TIFF, SVG unsupported
- Validate base64
- Verify actual image format
- Reject corrupt/invalid images
- No resizing, compression, conversion, or cropping

## Error Behavior

Decision #5 established:

- Immediate clear errors
- No automatic retries
- Provider failures are returned immediately
- No multiplication of provider calls

---

# 3. Decision #7 — MCP Key Provisioning & OpenCode Configuration

## Status

**LOCKED**

## Decision

Each user gets one dedicated MCP API key initially.

The key is generated from the authenticated frontend account, shown to the user exactly once, and stored only as a secure hash in the database.

OpenCode reads the key from an environment variable rather than storing the plaintext secret directly in `opencode.json`.

---

## 3.1 Why a Dedicated MCP Key?

Frontend authentication and MCP authentication are separate:

```text
Frontend login/session
        ≠
MCP authentication
```

OpenCode therefore does not need the user's frontend session credential.

---

## 3.2 Key Lifecycle

```text
Frontend
   ↓
Authenticated user
   ↓
Settings → MCP Access
   ↓
Generate MCP Key
   ├── hash → DB
   └── plaintext → show once
                       ↓
                User copies key
                       ↓
              VISION_MCP_KEY=...
                       ↓
                    OpenCode
                       ↓
             Authorization: Bearer ...
                       ↓
                  Vision MCP
                       ↓
                 Verify key
                       ↓
                   User UUID
```

---

## 3.3 Database Concept

Conceptually:

```text
mcp_credentials
----------------
id
user_id
key_hash
created_at
last_used_at
revoked_at
```

Exact schema remains unfinalized.

---

## 3.4 Key Storage

The raw MCP key is never stored in plaintext.

```text
Raw key
   ↓
Cryptographic hash
   ↓
Database
```

The exact key format/prefix and exact generation/hash library are not yet locked.

---

## 3.5 One Key Per User

Initially:

```text
1 user → 1 MCP key
```

Multiple keys per user are deferred.

---

## 3.6 Regeneration

```text
Old key
   ↓
Revoke
   ↓
Generate new key
   ↓
Show new plaintext once
```

The old key becomes invalid.

---

## 3.7 OpenCode Environment Variables

Current OpenCode documentation was specifically checked for this client-specific behavior.

OpenCode supports:

```text
{env:VARIABLE_NAME}
```

for variable substitution.

The intended configuration is:

```text
VISION_MCP_KEY=mcp_xxxxxxxxxxxxxxxxx
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

Therefore the plaintext key is not put directly into `opencode.json`.

---

## 3.8 Ready-to-Copy OpenCode Configuration

The frontend should provide a ready-to-copy configuration snippet like:

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

The key itself must not be embedded in the snippet.

---

## 3.9 MCP Access UI

A simple frontend section can show:

```text
MCP Access

Status: Configured
Created: <date>

[Regenerate MCP Key]
[Revoke MCP Access]
```

The plaintext secret is displayed only during generation/regeneration.

---

## 3.10 Decision #7 — Locked vs Deferred

### Locked

- Dedicated MCP API key
- Separate from frontend login/session
- One key per user initially
- Generated from authenticated frontend account
- Plaintext shown once
- Only hash stored
- Revocation
- Regeneration invalidates old key
- OpenCode environment-variable configuration
- `Authorization: Bearer {env:VISION_MCP_KEY}`
- `oauth: false` for API-key authentication
- Ready-to-copy OpenCode configuration

### Deferred / Not Locked

- Exact key prefix/format
- Exact random generation library
- Exact hashing algorithm/library
- Exact database schema
- Exact `last_used_at` behavior
- Token expiration policy
- Multiple MCP keys
- MCP OAuth
- Secret-file configuration using `{file:...}`
- Exact MCP setup UX

---

# 4. Decision #8 — MCP Endpoint & Transport Architecture

## Status

**LOCKED**

## Decision

Use:

> **Remote MCP over Streamable HTTP at `/mcp`, integrated into the same Python ASGI backend application as the normal API.**

No SSE and no stdio for the deployed architecture.

---

## 4.1 Transport

```text
Streamable HTTP → YES
Old HTTP + SSE  → NO
stdio           → NO for deployed server
```

Current OpenCode remote MCP configuration uses a remote URL, and the current MCP transport specification defines Streamable HTTP as the modern HTTP transport.

---

## 4.2 Why Not stdio?

stdio is useful when OpenCode launches a local MCP process:

```text
OpenCode
   ↓
spawn MCP process
   ↓
stdin/stdout
```

Our project instead has users, frontend authentication, database-backed profiles, MCP credentials, and a remotely deployed backend.

Therefore:

```text
OpenCode
   │ HTTPS
   ▼
Our server
```

is the correct primary architecture.

Local stdio support can be considered later if there is a concrete requirement.

---

## 4.3 Why Not SSE?

Older MCP tutorials may use an SSE endpoint such as:

```text
/mcp/sse
```

We will not build around that older transport.

Use Streamable HTTP instead.

---

## 4.4 Endpoint

The MCP endpoint is:

```text
https://your-domain.com/mcp
```

The normal API can coexist with it:

```text
https://your-domain.com/api/...
https://your-domain.com/mcp
```

The exact REST route structure is not part of this decision.

---

## 4.5 Same Python Backend

No separate MCP microservice initially.

```text
Python ASGI Backend
├── Normal API /api/...
├── MCP /mcp
├── Authentication
├── Database access
└── Vision service
```

The Python MCP SDK supports integrating the MCP server into an existing ASGI application.

This is deliberately simpler and lighter than deploying separate API and MCP services.

---

## 4.6 MCP Authentication Flow

```text
OpenCode
   │
   │ HTTPS
   │ Authorization: Bearer <MCP_KEY>
   ▼
/mcp
   ↓
Authenticate MCP key
   ↓
Identify user UUID
   ↓
Apply rate/concurrency limits
   ↓
Execute MCP tool
```

The backend derives identity from the credential; caller-supplied user IDs are not trusted.

---

## 4.7 HTTPS

The deployed endpoint uses HTTPS:

```text
OpenCode
   │ TLS/HTTPS
   ▼
https://your-domain.com/mcp
```

This protects the MCP credential in transit.

---

## 4.8 Origin Validation

Streamable HTTP has security requirements including Origin validation to mitigate DNS-rebinding attacks.

This is required in the eventual implementation.

The exact middleware/configuration is not yet locked.

---

## 4.9 Transport Implementation

Use the official Python MCP SDK's Streamable HTTP support rather than implementing MCP transport manually.

Conceptually:

```text
FastAPI / ASGI
      │
      ├── REST API
      │
      └── MCP SDK
             ↓
       Streamable HTTP
```

---

## 4.10 Decision #8 — Locked vs Deferred

### Locked

- Remote MCP
- Streamable HTTP
- `/mcp`
- HTTPS for deployed server
- Python ASGI backend
- MCP + normal API in same application
- Official Python MCP SDK
- MCP API-key authentication
- Origin validation required
- No separate MCP service initially
- No custom MCP transport implementation

### Deferred / Not Locked

- Exact ASGI framework
- Exact MCP SDK version
- Exact middleware configuration
- Exact deployment server
- Reverse proxy configuration
- TLS/proxy setup
- Containerization
- Whether a separate MCP service is ever useful
- Local-development stdio support

---

# 5. Decision #9 — Rate Limiting & Concurrency

## Status

**LOCKED**

## Decision

Per authenticated user:

```text
Maximum 20 vision calls per rolling 60 seconds
Maximum 3 concurrent vision calls
```

Both limits apply to:

```text
describe_image
ocr_image
```

The checks happen before the Vision LLM call.

If either limit is reached, the request is immediately rejected.

There is no queue and no automatic retry.

For the initial single-instance deployment, limiter state is kept in memory.

Redis is intentionally not introduced at this stage.

---

## 5.1 Why a Rolling Window?

A fixed window can allow boundary bursts:

```text
12:00:59 → 19 requests
12:01:01 → 19 requests
```

That could allow 38 calls in roughly two seconds.

A rolling window instead asks:

> How many calls has this user made during the previous 60 seconds?

This more accurately represents the intended 20-calls-per-minute rule.

---

## 5.2 Rolling Window Concept

```text
Current time
     ↓
<──────────── 60 seconds ────────────>
     │
     │ recent calls
     ▼
   [● ● ● ● ● ● ...]
```

When an old call becomes more than 60 seconds old, it leaves the active window.

---

## 5.3 Why Not Token Bucket?

Token bucket is useful when controlled bursts are desirable.

Our goal is simpler:

```text
20 calls in any rolling 60 seconds
```

Vision requests are expensive external LLM operations, so predictable limiting is preferred over burst-oriented behavior.

---

## 5.4 Concurrency Limit

Concurrency is separate from rate limiting.

At most three vision requests can be active for one user:

```text
Request A ───────── Vision LLM ───────┐
Request B ───────── Vision LLM ───────┤
Request C ───────── Vision LLM ───────┘
                                      3 active
```

A fourth simultaneous request is rejected:

```text
Request D
   ↓
3 already active
   ↓
REJECT
```

The concurrency slot is released when the request completes or fails.

---

## 5.5 No Queue

We do not queue requests:

```text
3 active
   ↓
4th request
   ↓
Immediate error
```

A queue would introduce additional memory use, latency, cancellation behavior, timeout handling, and operational complexity.

None is currently required.

---

## 5.6 No Automatic Retry

This follows Decision #5.

```text
Limit reached
   ↓
Immediate error
```

The backend does not automatically retry rejected requests.

Provider failures are also not automatically retried.

This avoids multiplying expensive Vision API calls.

---

## 5.7 Identity

Limits are keyed by authenticated user UUID:

```text
MCP API key
   ↓
User UUID
   ↓
Rate/concurrency state
```

The system does not trust a caller-supplied `user_id`.

---

## 5.8 Request Path

```text
OpenCode
   ↓
/mcp
   ↓
Authenticate MCP key
   ↓
Resolve user UUID
   ↓
Check rolling 20/min limit
   ├── exceeded → immediate error
   ↓
Check 3 concurrent limit
   ├── exceeded → immediate error
   ↓
Get active Vision Profile
   ↓
Execute tool
   ↓
Call Vision LLM
   ↓
Return result
   ↓
Release concurrency slot
```

The provider is never contacted when our own limits reject the request.

---

## 5.9 Why In-Memory?

The project explicitly targets lightweight deployment.

The limiter only needs tiny ephemeral state:

```text
User UUID
recent call timestamps
active call count
```

It does not store images or responses.

Adding Redis would introduce another service:

```text
Python backend
   ├── PostgreSQL
   └── Redis
```

That means extra RAM, CPU, deployment, configuration, monitoring, and operational complexity.

For a single backend instance, in-memory state is much lighter and sufficient.

---

## 5.10 Important In-Memory Caveat

In-memory state is local to a backend process.

With multiple processes/instances:

```text
Load Balancer
     │
 ┌───┴────┐
 ▼        ▼
App 1    App 2
 │        │
Limiter  Limiter
 A        B
```

the limiters do not automatically share state.

If the project later scales horizontally, a shared store such as Redis may become appropriate.

That is intentionally deferred.

---

## 5.11 Why Not PostgreSQL?

We will not write every vision-call timestamp to PostgreSQL just to enforce rate limits.

That would create unnecessary database traffic.

PostgreSQL remains responsible for persistent state such as:

```text
users
system_prompts
vision_profiles
mcp_credentials
```

Rate/concurrency state is temporary and stays in memory for v1.

---

## 5.12 Decision #9 — Locked vs Deferred

### Locked

- 20 vision calls per rolling 60 seconds per user
- 3 concurrent vision calls per user
- Applies to both MCP tools
- Moving/sliding window
- Immediate rejection
- No queue
- No automatic retry
- Keyed by authenticated user UUID
- Checks before Vision LLM call
- No provider call when rejected
- Concurrency slot released after completion/failure
- In-memory state for initial deployment
- No Redis initially
- No PostgreSQL rate-limit event storage

### Deferred / Not Locked

- Exact rate-limiter library
- Exact in-memory data structure
- Exact machine-readable error codes
- Exact MCP error object
- Exact HTTP status mapping
- Persistence across restarts
- Distributed rate limiting
- Redis or another shared limiter for future scaling

---

# 6. Combined Architecture After Decisions #7–#9

```text
                         ┌──────────────────────┐
                         │       Frontend       │
                         │      TypeScript      │
                         └──────────┬───────────┘
                                    │
                              HTTPS / API
                                    │
                                    ▼
                    ┌────────────────────────────────┐
                    │       Python ASGI Backend      │
                    │                                │
                    │  ┌──────────────────────────┐  │
                    │  │ Normal API /api/...      │  │
                    │  └──────────────────────────┘  │
                    │                                │
                    │  ┌──────────────────────────┐  │
OpenCode ──────────►│  │ MCP Streamable HTTP     │  │
                    │  │ /mcp                    │  │
                    │  └─────────────┬────────────┘  │
                    │                │               │
                    │                ▼               │
                    │        Authenticate Key        │
                    │                │               │
                    │                ▼               │
                    │          User UUID              │
                    │                │               │
                    │                ▼               │
                    │    Rate 20/min + Concurrent 3  │
                    │                │               │
                    │                ▼               │
                    │      Active Vision Profile     │
                    │                │               │
                    │                ▼               │
                    │         Vision Service         │
                    └────────────────┬───────────────┘
                                     │
                                     ▼
                              Vision LLM API
```

---

# 7. OpenCode → MCP Authentication Flow

```text
User
 ↓
VISION_MCP_KEY=mcp_xxx
 ↓
OpenCode
 ↓
{env:VISION_MCP_KEY}
 ↓
Authorization: Bearer mcp_xxx
 ↓
https://your-domain.com/mcp
 ↓
Backend verifies key
 ↓
User UUID
 ↓
User-specific configuration
```

---

# 8. Complete Vision Request Flow

```text
┌──────────┐
│ OpenCode │
└────┬─────┘
     │
     │ MCP Streamable HTTP
     │ Bearer MCP Key
     ▼
┌─────────────────┐
│ /mcp            │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Authenticate    │
│ MCP credential  │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Resolve user    │
│ UUID            │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Rate: 20/60 sec │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Concurrent: 3   │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ MCP tool        │
│ describe_image  │
│ OR ocr_image    │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Validate image  │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Get active      │
│ Vision Profile  │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Build vision    │
│ LLM request     │
└────┬────────────┘
     │
     ▼
┌──────────────────┐
│ OpenAI-compatible│
│ Vision endpoint  │
└────┬─────────────┘
     │
     ▼
┌─────────────────┐
│ Return result   │
│ to OpenCode     │
└─────────────────┘
```

---

# 9. Lightweight Deployment Philosophy

Current preferred shape:

```text
                Low-spec Server
        ┌───────────────────────────┐
        │                           │
        │ Python ASGI Backend       │
        │ ├── REST API              │
        │ ├── MCP /mcp              │
        │ ├── Auth                  │
        │ ├── Vision service        │
        │ └── In-memory limiter     │
        │                           │
        │ PostgreSQL                │
        │                           │
        └───────────────────────────┘
```

We deliberately avoid introducing:

```text
Redis
Kafka
RabbitMQ
Microservices
Vector DB
LangGraph
RAG infrastructure
Separate MCP service
Request queues
```

unless an actual future requirement justifies them.

---

# 10. Assumptions

1. Initial deployment uses a single backend instance/process or otherwise has shared in-memory limiter state.
2. Horizontal scaling is not currently required.
3. Lightweight, low-spec deployment is a primary design goal.
4. OpenCode's current remote MCP support uses Streamable HTTP.
5. OpenCode supports environment-variable substitution for MCP headers.
6. MCP API keys are sufficient for initial machine-to-machine authentication.
7. One MCP key per user is sufficient initially.
8. MCP OAuth is not currently required.
9. Vision providers use OpenAI-compatible endpoints.
10. Rate limiting protects provider usage and backend resources.
11. Vision requests are expensive enough that controlled concurrency is useful.
12. Durable rate-limit state across restarts is not currently required.
13. Distributed rate limiting is not currently required.

---

# 11. Explicitly Deferred Complexity

Do not implement these merely because they might be useful later:

- Redis
- Distributed rate limiting
- Multiple backend instances
- Multiple MCP keys
- MCP OAuth
- Secret-file OpenCode configuration
- MCP SSE compatibility
- Separate MCP microservice
- Request queues
- Automatic retries
- Persistent rate-limit event database
- Custom MCP transport
- Provider-specific integrations beyond OpenAI-compatible endpoints
- Advanced model parameters
- Additional MCP tools

Each should be introduced only when an actual requirement appears.

---

# 12. Current Locked Decisions Summary

| Decision | Topic | Status |
|---|---|---|
| #7 | MCP key provisioning & OpenCode configuration | LOCKED |
| #8 | MCP endpoint & transport architecture | LOCKED |
| #9 | Rate limiting & concurrency | LOCKED |

### Decision #7

```text
One MCP key/user
      ↓
Generate from frontend
      ↓
Hash → DB
Plaintext → show once
      ↓
VISION_MCP_KEY
      ↓
OpenCode {env:VISION_MCP_KEY}
      ↓
Authorization: Bearer ...
```

### Decision #8

```text
OpenCode
    │ HTTPS
    ▼
/mcp
    │
    ▼
Streamable HTTP
    │
    ▼
Python ASGI backend
```

### Decision #9

```text
Authenticated user
      ├── max 20 calls / rolling 60 sec
      └── max 3 concurrent calls
```

Rejected requests:

```text
Immediate error
No queue
No automatic retry
No provider call
```

---

# 13. What We Have NOT Decided Yet

## Authentication

- Exact frontend session architecture
- Exact password hashing implementation
- Google OAuth implementation details
- Exact MCP key format
- Exact MCP credential schema

## Backend

- Exact Python framework
- Exact ASGI server
- Exact project structure
- ORM
- Migration tool
- MCP SDK version

## Vision Request Execution

- Exact LangChain integration
- Exact OpenAI-compatible client
- Request timeout
- Provider response parsing
- Provider error normalization
- Exact system/user/image message construction

## Image Processing

- Exact decoding library
- Exact content detection implementation
- Exact implementation of size/resolution checks

## Error Protocol

- HTTP status codes
- MCP error object
- Machine-readable error codes
- Logging policy
- User-facing error formatting

## Deployment

- Reverse proxy
- TLS configuration
- Domain setup
- Process manager
- Containerization
- Database deployment configuration

These remain open and should be decided only when their requirements are addressed.

---

# 14. Core Design Principle

> **Do the simplest thing that fully satisfies the current requirements.**

For each future decision:

```text
Do we actually need this?
        │
   ┌────┴────┐
   │         │
  Yes        No
   │         │
Design it   Defer it
```

The objective is not to build a theoretically scalable distributed system from day one.

The objective is to build a clean, secure, understandable Vision MCP service that runs comfortably on modest hardware and can be expanded when real requirements justify the additional complexity.
