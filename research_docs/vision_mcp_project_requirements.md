# Vision MCP / OpenCode Project — Requirements & Decisions

**Status:** Requirements gathering / design phase  
**Last updated:** 2026-09-03

---

## 1. Project Goal

The project is a Python backend + TypeScript frontend system that provides a **vision sidecar/gateway for OpenCode**.

The core problem:

- The user may select a primary LLM in OpenCode that does **not support vision/image recognition**.
- The user may nevertheless have API access to one or more vision-capable LLMs.
- The user does **not** want to switch the primary OpenCode model merely because it lacks vision.
- Instead, the primary LLM should be able to call an authenticated MCP tool when it needs to inspect an image.
- The MCP/backend sends the image and the primary LLM's specific request to the user's configured vision model.
- The vision model returns the requested information.
- The primary LLM then continues its reasoning using that result.

### Core philosophy

Keep the implementation:

- very simple
- clear
- easy to understand
- lightweight
- free of unnecessary infrastructure or abstraction unless a requirement actually needs it

Do **not** prematurely add:

- agent frameworks
- LangGraph
- RAG
- vector databases
- queues
- caching
- microservices
- fallback model routing
- automatic model selection
- dashboards
- unnecessary provider integrations

---

# 2. High-Level Concept

The MCP is best understood as a:

> **Visual perception / vision sidecar / gateway**

It is **not** an autonomous agent.

The primary LLM remains responsible for reasoning.

Conceptually:

```text
                         OpenCode
                            |
                            | authenticated MCP request
                            | image + user prompt
                            v
                  +----------------------+
                  | Python Backend / MCP |
                  +----------------------+
                            |
                            | identify authenticated user
                            v
                  +----------------------+
                  | Active Vision Profile|
                  +----------------------+
                            |
                +-----------+-----------+
                |                       |
                v                       v
          System Prompt        Universal Extra Instructions
                                      |
                                      | Image Description only
                                      v
                             Request construction
                                      |
                                      v
                              Vision LLM endpoint
                                      |
                                      v
                                  Result
                                      |
                                      v
                                  OpenCode
```

---

# 3. Technology Decisions

## Backend

**Python**

The whole backend will be Python.

It will expose:

1. normal authenticated API endpoints for the frontend
2. authenticated MCP endpoints for OpenCode

## Frontend

**TypeScript**

The frontend will communicate with the backend through authenticated API endpoints.

## Database

A database is required because the application has:

- users
- authentication information
- System Prompts
- Vision Profiles
- encrypted API keys
- configuration/settings

PostgreSQL vs MySQL has been discussed, with PostgreSQL currently leaning as the preferred choice, but this is **not yet locked**.

The database should work well on low-resource servers.

## LangChain

The backend will use **LangChain in a simple/narrow way**.

The intended purpose is primarily to construct the vision-model request from:

- System Prompt
- Universal Extra Instructions when applicable
- User Prompt
- Image

and invoke the selected model.

LangChain is **not** intended to turn this into an autonomous agent system.

---

# 4. Authentication Requirements

Authentication is required.

The application should support:

- Email/password authentication
- Google OAuth, if practical

## No public signup

There should be **no public account creation/signup feature**.

Instead, an administrator/user with appropriate access should be able to run a script that:

- accesses the database
- creates/provisions users
- establishes their authentication details

The exact provisioning mechanism is still to be designed.

## MCP authentication

OpenCode's MCP access must also be authenticated.

The MCP/backend must know which application user is making the request.

The authenticated user identity should determine which:

- System Prompts
- Vision Profiles
- API keys
- settings

the MCP can access.

### Important security rule

Do **not** trust a user ID supplied by the MCP caller as the sole source of identity.

Conceptually:

```text
OpenCode
   |
   | authenticated credential
   v
MCP
   |
   v
Authenticate request
   |
   v
Authenticated User UUID
   |
   +----> User's resources only
```

This prevents a user from simply changing:

```text
user_id = A
```

to:

```text
user_id = B
```

and accessing another user's resources.

The exact session/token/authentication mechanism is **not yet locked**.

---

# 5. System Prompts

There will be a frontend page called:

> **System Prompts**

Users can create and manage System Prompts.

Each System Prompt should have at least:

```text
id / UUID
user_id / owning user UUID
title
prompt content
created_at
updated_at
```

## Ownership

Every System Prompt belongs to a specific user.

The owning user's UUID is important for preventing cross-user data leaks.

Conceptually:

```text
users
  |
  +---- system_prompts
           |
           +---- user_id
```

A user should only be able to read/update/delete their own prompts.

## Vision Profile relationship

A Vision Profile should **reference** a System Prompt by UUID.

The actual prompt text should not be duplicated into every Vision Profile.

Conceptually:

```text
Vision Profile
    |
    | system_prompt_id
    v
System Prompt
```

This allows the user to manage prompts independently.

The exact deletion behavior when a System Prompt is referenced by a Vision Profile is still undecided.

---

# 6. Vision Profiles

There will be a frontend page called:

> **Vision Profiles**

A Vision Profile represents a complete configuration for a vision-capable LLM endpoint.

## Important model-selection rule

The **user chooses the Vision Profile**.

The primary LLM does **not** choose the vision model.

The MCP does **not** intelligently choose the vision model.

There is no automatic routing/fallback in the current design.

---

# 7. Active Vision Profile

We discussed two similar approaches:

- Option A: one active profile
- Option C: a configured active profile

We chose the concept represented by **Option C** because it is clearer from the user's point of view.

There is:

> **One Active Vision Profile per user.**

The user selects it from the frontend.

Example UI:

```text
Vision Profiles

+-----------------------------------+
| Gemini Vision                     |
|                                   |
| Model: gemini-vision-model        |
| System Prompt: General Analysis   |
| API Key: ✓ Configured             |
|                                   |
| [ Active ] [ Edit ] [ Delete ]    |
+-----------------------------------+

+-----------------------------------+
| Qwen Vision                       |
|                                   |
| Model: qwen-vl-model               |
| System Prompt: Screenshot Analysis|
| API Key: ✓ Configured             |
|                                   |
| [ Set Active ] [ Edit ] [ Delete ]|
+-----------------------------------+
```

The MCP simply asks:

```text
Which Vision Profile is active for this authenticated user?
```

It then uses that profile.

No model-selection logic is required in the MCP.

---

# 8. Current Vision Profile Fields

The current proposed structure is:

```text
Vision Profile
├── Name
├── Endpoint / Base URL
├── Model
├── API Key
├── System Prompt
└── Active
```

Conceptually, the database record may look like:

```text
vision_profiles

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

The exact final schema is **not yet locked**.

---

# 9. OpenAI-Compatible API Decision — LOCKED

We discussed how OpenCode handles different custom endpoints and used that as a design reference.

For the initial version:

> **Only OpenAI-compatible LLM endpoints will be supported.**

This is now a **locked decision**.

The idea is to avoid implementing separate provider integrations initially.

The user can provide:

```text
Endpoint
Model
API Key
```

as long as the endpoint exposes an OpenAI-compatible API.

This allows the system to work with many different providers and custom/self-hosted endpoints without implementing a separate adapter for each provider.

## Current conceptual request path

```text
Vision Profile
    |
    +-- Endpoint
    +-- Model
    +-- API Key
    |
    v
OpenAI-compatible client/request
    |
    v
Configured vision endpoint
```

## Provider-specific integrations

Native Anthropic/Google/etc. integrations are **not part of the initial implementation**.

If a provider does not expose an OpenAI-compatible endpoint, it is outside the initial supported scope.

A future provider abstraction can be added later if there is a concrete need.

---

# 10. API Key Storage

API keys are sensitive and should **not** be stored as plaintext.

The current recommended design is:

> **Application-level encryption at rest**

The database stores encrypted API-key ciphertext.

A master encryption key is kept **outside the database**, for example through environment/secret injection.

Conceptually:

```text
User enters API key
        |
        v
Python backend
        |
        | encrypt
        v
Database
(encrypted key only)
```

During an LLM request:

```text
Database
   |
   | encrypted API key
   v
Backend
   |
   | decrypt temporarily in memory
   v
Vision provider request
   |
   v
Result
```

The decrypted API key should not be:

- returned to the frontend
- exposed through an API endpoint
- written to logs
- included in normal application output

The frontend should instead see something like:

```text
API Key: ✓ Configured
```

If the user wants to replace the key, they enter a new one.

### Security boundary

This design protects API keys from a database-only compromise because the attacker would also need the application encryption key.

It does **not** protect against a full compromise of the application server/runtime itself.

The exact encryption library/mechanism has not yet been locked, although Python `cryptography` / Fernet was discussed as a simple candidate.

---

# 11. Modes

There are at least two modes:

1. **Image Description**
2. **OCR**

The user explicitly clarified that the second mode is **OCR**.

---

# 12. Image Description Mode — LOCKED

Image Description mode combines:

1. Vision Profile's System Prompt
2. Universal Extra Instructions
3. User Prompt received through MCP
4. Image

Conceptually:

```text
System Prompt
      +
Universal Extra Instructions
      +
User Prompt
      +
Image
      |
      v
Vision LLM
      |
      v
Final result
```

## System Prompt

The System Prompt comes from the selected Vision Profile.

## Universal Extra Instructions

There is exactly **one universal Extra Instructions prompt**.

It applies to:

> **all Vision Profiles in Image Description mode**

It is not duplicated into each profile.

---

# 13. OCR Mode — LOCKED

OCR mode uses:

- System Prompt
- User Prompt
- Image

The Universal Extra Instructions are **NOT included** in OCR mode.

Conceptually:

```text
System Prompt
      +
User Prompt
      +
Image
      |
      v
Vision LLM
      |
      v
OCR/result
```

## OCR behavior — Option B chosen

OCR is **OCR + user instruction**, rather than only blind text extraction.

The user can give instructions such as:

```text
Extract all the text.
```

or:

```text
Extract the text and preserve the table structure.
```

or:

```text
Extract the error message from this screenshot.
```

or:

```text
Extract the text exactly as written.
```

This means OCR mode is primarily focused on text extraction, but the user prompt can control how that extracted information should be returned/handled.

A more formal structured OCR response format has **not** been selected.

---

# 14. Universal Extra Instructions

There is exactly one global Universal Extra Instructions prompt.

Rules:

- Applies to all Vision Profiles
- Applies only to Image Description mode
- Does not apply to OCR mode
- Is not duplicated inside Vision Profiles

Conceptually:

```text
Image Description:

Vision Profile System Prompt
          +
Universal Extra Instructions
          +
User Prompt
          +
Image
```

and:

```text
OCR:

Vision Profile System Prompt
          +
User Prompt
          +
Image
```

The exact frontend location and database representation are still to be decided.

---

# 15. MCP Request Concept

The MCP should receive both:

- a picture
- a user prompt

at the same time.

Conceptually:

```text
MCP request

image = <picture>
prompt = "What error is visible in this screenshot?"
```

The primary LLM does not need to provide:

- the Vision Profile
- the System Prompt
- the API key
- the endpoint
- the model

Those are backend configuration.

The backend derives them from:

```text
Authenticated User
       |
       v
Active Vision Profile
```

---

# 16. Current MCP Flow

The intended flow is:

```text
OpenCode
   |
   | authenticated MCP request
   | image + user prompt
   v
Python MCP/backend
   |
   | authenticate user
   v
Authenticated User UUID
   |
   v
Active Vision Profile
   |
   +--> System Prompt
   |
   +--> Endpoint
   |
   +--> Model
   |
   +--> Encrypted API Key
   |
   v
Decrypt API key temporarily
   |
   v
Construct LangChain/model request
   |
   +--> Image Description:
   |      System Prompt
   |      + Universal Extra Instructions
   |      + User Prompt
   |      + Image
   |
   +--> OCR:
          System Prompt
          + User Prompt
          + Image
   |
   v
OpenAI-compatible vision endpoint
   |
   v
Vision model response
   |
   v
Return result to OpenCode
```

---

# 17. Frontend Pages Discussed

Current frontend concepts:

## Login / Authentication

Handles authenticated access.

## System Prompts

Allows users to:

- create prompts
- edit prompts
- delete prompts
- view prompts

Each prompt belongs to the authenticated user.

## Vision Profiles

Allows users to:

- create profiles
- edit profiles
- delete profiles
- select the Active Vision Profile

## Universal Extra Instructions

A settings area/page for managing the single global Extra Instructions prompt is expected, but the exact page name/location has not been finalized.

---

# 18. Vision Profile Creation Mock

Current conceptual mock:

```text
Create Vision Profile

Name
[____________________________]

Endpoint / Base URL
[____________________________]

Model
[____________________________]

API Key
[____________________________]

System Prompt
[ Select System Prompt ▼ ]

[ Create Profile ]
```

Because OpenAI-compatible endpoints are currently the only supported format, an API-format dropdown is **not currently necessary**.

We had previously considered:

```text
API Format
[ OpenAI Compatible ▼ ]
```

but after deciding to support only OpenAI compatibility initially, this can simply be a fixed implementation detail rather than a user-facing field.

---

# 19. Vision Profile Display Mock

Example:

```text
Vision Profiles

+---------------------------------------+
| Gemini Vision                         |
|                                       |
| Model: gemini-vision-model            |
| System Prompt: General Analysis       |
| API Key: ✓ Configured                 |
|                                       |
| [ Active ] [ Edit ] [ Delete ]        |
+---------------------------------------+

+---------------------------------------+
| Screenshot Analyzer                   |
|                                       |
| Model: qwen-vl-model                  |
| System Prompt: Screenshot Analysis    |
| API Key: ✓ Configured                 |
|                                       |
| [ Set Active ] [ Edit ] [ Delete ]    |
+---------------------------------------+
```

The exact UI styling is not important yet. The mock exists to communicate the intended behavior.

---

# 20. Data Isolation Model

Every user-owned object should be scoped to the authenticated user's UUID.

Conceptually:

```text
users
 |
 +----------------------+
 |                      |
 v                      v
system_prompts      vision_profiles
 |                      |
 | user_id              | user_id
 |                      |
 +----------+-----------+
            |
            v
     authenticated user
```

A Vision Profile also references its System Prompt:

```text
vision_profiles.system_prompt_id
                |
                v
        system_prompts.id
```

Queries should always be scoped by authenticated user ownership.

Do not rely on frontend-supplied ownership IDs.

---

# 21. Image Format Requirements

The user wants support for image formats that are broadly/common across vision-capable LLMs.

The baseline formats discussed were:

- JPEG / JPG
- PNG
- WebP
- GIF

This is **not yet fully locked**.

Formats such as TIFF, BMP, SVG, HEIC, etc. have not been committed to.

Image size limits, MIME validation, animated GIF behavior, and provider-specific constraints are still undecided.

---

# 22. Things Explicitly NOT Decided Yet

The following should remain open until discussed:

## Vision Profile advanced configuration

Whether to expose:

- temperature
- max output tokens
- top-p
- other model parameters
- custom headers

The current inclination is to keep this minimal unless there is a concrete need.

## MCP tool design

Still need to decide:

- exact MCP tool name
- exact arguments
- whether mode is an argument
- whether Image Description and OCR are one tool or separate tools
- exact image/content-block representation
- response format
- error format

## Image handling

Still need to decide:

- exact supported formats
- maximum file size
- maximum request size
- whether images are ever persisted
- MIME validation
- timeouts
- provider failures
- malformed image behavior

## System Prompt behavior

Still need to decide:

- exact frontend interactions
- deletion rules when referenced
- title uniqueness requirements
- whether empty prompts are allowed

## Universal Extra Instructions

Still need to decide:

- exact UI location
- whether empty is allowed
- default value
- DB representation
- update behavior

## Authentication implementation

Still need to decide:

- session vs JWT/token architecture
- password hashing details
- Google OAuth implementation
- MCP credential type
- token/session expiration
- provisioning script details
- logout/session revocation behavior

## Database

Still need to decide:

- PostgreSQL vs MySQL
- exact schema
- indexes
- foreign keys
- cascading/deletion behavior
- auth-related tables

## REST API

Still need to define the exact frontend API endpoints and request/response shapes.

## Deployment

Still need to decide:

- Docker vs direct deployment
- reverse proxy
- TLS
- database deployment
- MCP transport/exposure
- secret/environment management
- frontend hosting

---

# 23. Recommended Order for Remaining Decisions

To avoid designing things prematurely, continue in roughly this order:

1. **Vision Profile advanced configuration**
   - Keep minimal or add optional fields?

2. **MCP tool design**
   - Exact tool(s), arguments, image transmission, mode, output.

3. **Image handling**
   - Formats, size limits, persistence, validation.

4. **System Prompt behavior**
   - CRUD and reference/deletion rules.

5. **Universal Extra Instructions**
   - UI and storage behavior.

6. **Authentication implementation**
   - Web authentication + MCP authentication.

7. **Database schema**
   - Final tables and relationships after requirements are settled.

8. **REST API contract**
   - Frontend/backend endpoints.

9. **Deployment architecture**
   - Infrastructure and operational details.

This order is intended to keep the design simple and prevent premature architecture decisions.

---

# 24. Current Locked Decisions — Quick Reference

| Area | Current decision |
|---|---|
| Backend | Python |
| Frontend | TypeScript |
| Database | Required; PostgreSQL/MySQL not yet locked |
| LLM orchestration | Simple LangChain usage |
| MCP role | Vision sidecar/gateway, not autonomous agent |
| Vision model selection | User-controlled |
| Primary LLM chooses model? | No |
| MCP chooses model? | No |
| Active profiles | One active Vision Profile per user |
| API format | **OpenAI-compatible only initially** |
| Custom endpoints | Supported |
| API key storage | Encrypted at rest |
| API key returned to frontend | No |
| System Prompts | Separate user-owned resources |
| Vision Profiles | Reference System Prompt by UUID |
| Modes | Image Description + OCR |
| Image Description | System + Universal Extra + User Prompt + Image |
| OCR | System + User Prompt + Image |
| Universal Extra in OCR | No |
| OCR behavior | **OCR + user instruction** |
| MCP input | Image + user prompt |
| Public signup | No |
| Authentication | Email/password + Google OAuth if practical |
| MCP authentication | Required |
| User isolation | Authenticated user UUID |
| Image formats | Common formats; exact list TBD |

---

# 25. Current Design Snapshot

At this point, the simplest coherent design is:

```text
                         USER
                          |
              +-----------+-----------+
              |                       |
              v                       v
          TypeScript UI            OpenCode
              |                       |
              | authenticated         | authenticated MCP
              v                       v
       Python REST API          Python MCP endpoint
              |                       |
              +-----------+-----------+
                          |
                          v
                   Authenticated User
                          |
                          v
                 Active Vision Profile
                          |
            +-------------+-------------+
            |                           |
            v                           v
      System Prompt             Encrypted API Key
            |                           |
            +-------------+-------------+
                          |
                          v
                  Request Construction
                          |
             +------------+-------------+
             |                          |
             v                          v
     Image Description                OCR
             |                          |
     System Prompt              System Prompt
             + Universal Extra          +
             + User Prompt              User Prompt
             + Image                    + Image
             |                          |
             +------------+-------------+
                          |
                          v
                   LangChain / Model
                          |
                          v
             OpenAI-Compatible Endpoint
                          |
                          v
                    Vision LLM
                          |
                          v
                       Result
                          |
                          v
                      OpenCode
```

---

# 26. Important Design Principle Going Forward

Do not add a feature merely because it is common in other LLM systems.

For every proposed configuration or component, ask:

> **Do we actually need this for the requirements we've established?**

If the answer is no, leave it out for now.

The goal is a small, understandable system that solves the specific problem:

> **Let a non-vision primary LLM in OpenCode obtain image understanding from a user-selected vision model through an authenticated MCP gateway.**
