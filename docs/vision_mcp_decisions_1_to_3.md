# Vision MCP Project — Decisions #1 to #3

## Purpose

This document records the requirements, reasoning, assumptions, flows, and decisions established for the Vision MCP project through Decision #3.

The project lets a primary LLM used through OpenCode inspect images through a separate, user-configured vision-capable LLM, without requiring the primary LLM itself to support vision.

The implementation is intentionally being kept simple. Architecture and technology choices beyond what is required are being deferred until the relevant requirements are settled.

---

# 1. Project Concept

## Problem

The user may select a primary LLM in OpenCode that does not support image/vision input, while also having API access to other vision-capable LLMs.

The desired behavior is:

```text
                    +---------------------+
                    |      OpenCode       |
                    |                     |
                    |    Primary LLM      |
                    +----------+----------+
                               |
                               | Needs image understanding
                               v
                    +---------------------+
                    |     MCP Server       |
                    |                     |
                    | describe_image      |
                    | or                  |
                    | ocr_image           |
                    +----------+----------+
                               |
                               | User's active Vision Profile
                               v
                    +---------------------+
                    |     Vision LLM       |
                    |                     |
                    | Endpoint + Model     |
                    +----------+----------+
                               |
                               | Result
                               v
                    +---------------------+
                    |      OpenCode       |
                    |    Primary LLM      |
                    +---------------------+
```

## Core principle

The primary LLM remains the main reasoning model. It calls an MCP tool when it needs visual information. The MCP sends the image and request to the configured vision LLM. The result is returned to OpenCode so the primary LLM can continue reasoning.

The MCP is a **vision perception sidecar/gateway**, not an autonomous agent.

---

# 2. Core Principles Established So Far

## Primary LLM chooses the operation

The primary LLM can choose whether it needs:

- image description/analysis
- OCR/text extraction

It does **not** choose:

- Vision Profile
- vision model
- API key
- endpoint

Those are determined by the authenticated user's configuration.

```text
Primary LLM
    |
    | chooses operation
    v
+-------------------------+
| describe_image          |
|          OR             |
| ocr_image               |
+------------+------------+
             |
             v
       MCP Backend
             |
             | authenticated user
             v
   User's Active Vision Profile
             |
             +-- endpoint
             +-- model
             +-- API key
             +-- system prompt
             |
             v
        Vision LLM
```

There is deliberately **no second AI decision** inside the backend.

---

# 3. Decision #1 — Vision Profile Configuration

## Status

**LOCKED**

## Selected option

**Minimal Configuration / Option A**

Each Vision Profile contains only what is currently necessary:

```text
Name
Endpoint / Base URL
Model
API Key
System Prompt
Active status
```

No advanced model parameters are included initially.

## Conceptual database record

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

The exact database schema is **not locked yet**. This is the current conceptual model.

---

## Fields

### Name

User-facing profile name.

Examples:

```text
Gemini Vision
Screenshot Analyzer
```

### Endpoint / Base URL

The URL of the OpenAI-compatible API endpoint.

### Model

The model identifier expected by that endpoint.

The MCP does not select a model dynamically. It uses the model configured in the user's active Vision Profile.

### API Key

The credential used to call the endpoint.

Security requirements:

- Do not store API keys as plaintext.
- Encrypt them at rest.
- Keep the encryption master key outside the database, such as an environment variable or injected secret.
- Python `cryptography` / Fernet is a candidate implementation, but the exact mechanism is not locked.
- Never return decrypted keys to the frontend.
- Frontend can receive something like `has_api_key: true`.
- Replacing a key requires entering a new key.
- Decrypt only when needed for the provider request.
- Do not log the decrypted key.

This protects against a database-only compromise. It does not protect against a complete compromise of the application environment containing the encryption master key.

### System Prompt

Each Vision Profile references a System Prompt by ID/UUID rather than duplicating prompt text.

```text
Vision Profile
      |
      | system_prompt_id
      v
System Prompt
```

### Active status

There is exactly **one active Vision Profile per user**.

The user selects the active profile in the frontend.

The MCP uses that profile deterministically.

The primary LLM cannot select a different profile.

---

# 4. Vision Profile UI

## Create Profile

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
[ Select System Prompt v ]

[ Create Profile ]
```

## Profile display

```text
Vision Profiles

+---------------------------------------+
| Gemini Vision                         |
|                                       |
| Model: gemini-vision-model            |
| System Prompt: General Analysis       |
| API Key: Configured                   |
|                                       |
| [ Active ] [ Edit ] [ Delete ]        |
+---------------------------------------+

+---------------------------------------+
| Screenshot Analyzer                   |
|                                       |
| Model: qwen-vl-model                  |
| System Prompt: Screenshot Analysis    |
| API Key: Configured                   |
|                                       |
| [ Set Active ] [ Edit ] [ Delete ]    |
+---------------------------------------+
```

The exact visual design is not locked.

---

# 5. Advanced Vision Profile Parameters

## Status

**DEFERRED**

The initial profile does NOT include:

- temperature
- max output tokens
- top-p
- arbitrary model parameters
- custom headers

The reason is simplicity. These can be added later if an actual requirement appears.

---

# 6. Custom Headers

## Current decision

**NOT supported initially.**

The first implementation supports OpenAI-compatible endpoints and does not provide an arbitrary custom-header editor.

Some providers may require extra headers such as project identifiers, but adding arbitrary headers introduces unnecessary configuration and security complexity at this stage.

Custom headers are deferred unless a real provider requirement makes them necessary.

---

# 7. API Compatibility Decision

## Status

**LOCKED**

The first implementation supports:

> **OpenAI-compatible endpoints only.**

The profile supplies:

```text
Endpoint
Model
API Key
```

and the backend communicates using the OpenAI-compatible request format.

## Not included initially

Native provider-specific integrations such as:

```text
Anthropic native API
Google native API
Other provider-specific APIs
```

are not separate integrations in the first version.

Provider-specific adapters can be added later if actually needed.

---

# 8. LangChain Usage

LangChain will be used narrowly in the backend to construct/invoke the configured vision LLM request.

It is **not** being used to introduce:

- LangGraph
- RAG
- vector databases
- autonomous agents
- complex agent chains
- unnecessary orchestration

The intended request composition is:

```text
System Prompt
      +
Additional instructions when applicable
      +
User Prompt
      +
Image
      |
      v
Vision LLM
      |
      v
Result
```

The exact LangChain package/classes are not locked yet.

---

# 9. Decision #2 — MCP Tool Design

## Status

**LOCKED**

The MCP exposes two separate tools:

```text
describe_image(image, prompt)
```

and

```text
ocr_image(image, prompt)
```

---

# 10. Why Two Tools?

The two operations have different purposes.

## Image Description

Used when the primary LLM wants to understand an image.

Examples:

```text
Tell me what is happening in this screenshot.
Why is this UI displaying an error?
Describe the diagram.
Explain what this image contains.
```

## OCR

Used when the primary LLM primarily needs text extracted.

Examples:

```text
Extract all the text.
Extract the error message.
Read the text exactly as written.
Extract the text and preserve the table structure.
```

Separate tools make the intent explicit and avoid an extra `mode` argument.

---

# 11. Backend Decision Flow

The backend does **not** analyze the prompt and decide whether it is OCR or description.

The tool name determines the operation.

```text
Primary LLM
      |
      +---- calls describe_image ----> Image Description Flow
      |
      +---- calls ocr_image ---------> OCR Flow
```

There is no AI router in the backend.

---

# 12. Image Description Flow

When the primary LLM calls:

```text
describe_image(
    image = <image>,
    prompt = "Tell me why this application is showing this error."
)
```

the backend performs:

```text
1. Authenticate MCP request
        |
2. Identify authenticated user
        |
3. Get that user's active Vision Profile
        |
4. Get the System Prompt referenced by that profile
        |
5. Obtain/decrypt the profile API key
        |
6. Build the vision request
        |
7. Send image + prompts to configured
   OpenAI-compatible Vision LLM
        |
8. Receive result
        |
9. Return result to OpenCode
```

Prompt composition:

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
Result
```

---

# 13. OCR Flow

When the primary LLM calls:

```text
ocr_image(
    image = <image>,
    prompt = "Extract the exact error message."
)
```

the same authentication/profile lookup process occurs.

Prompt composition:

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
Result
```

**Universal Extra Instructions are not included in OCR.**

Example result:

```text
KeyError: 'username'
```

---

# 14. Universal Extra Instructions

There is exactly **one universal Extra Instructions prompt**.

It is global rather than profile-specific.

## Locked behavior

```text
Image Description -> YES
OCR                -> NO
```

Therefore:

### Image Description

```text
System Prompt
+
Universal Extra Instructions
+
User Prompt
+
Image
```

### OCR

```text
System Prompt
+
User Prompt
+
Image
```

The exact frontend location for managing Universal Extra Instructions is not locked yet.

---

# 15. MCP Tool Responsibilities

## `describe_image`

Conceptual description:

```text
Analyze an image using the user's active Vision Profile.
Provide the image and explain what you need to know.
```

Arguments:

```text
image
prompt
```

It does not accept:

```text
profile_id
model
endpoint
api_key
```

because those are controlled by the authenticated user's configuration.

## `ocr_image`

Conceptual description:

```text
Extract/read text from an image using the user's active Vision Profile.
Provide the image and explain how the text should be extracted or returned.
```

Arguments:

```text
image
prompt
```

It also does not accept profile/model/API-key selection.

---

# 16. User/Profile Isolation

The MCP request must identify an authenticated application user.

The backend must **not** trust a caller-supplied `user_id` to determine ownership.

Instead:

```text
Authenticated MCP credentials
          |
          v
Authenticated User UUID
          |
          v
User's Vision Profiles
          |
          v
Active Vision Profile
```

This prevents one user from accessing another user's:

- Vision Profiles
- System Prompts
- API keys
- configuration

---

# 17. Decision #3 — Image Transmission

## Status

**LOCKED**

The project will use MCP's **ImageContent** representation for images.

The relevant MCP image structure contains:

```text
type
data
mimeType
```

with optional annotations/metadata.

Conceptually:

```json
{
  "type": "image",
  "data": "<base64-encoded image>",
  "mimeType": "image/png"
}
```

The image data is base64 encoded and the MIME type identifies the image format.

---

# 18. ImageContent Structure

Conceptually:

```text
ImageContent
|
+-- type
|     +-- "image"
|
+-- data
|     +-- base64-encoded image data
|
+-- mimeType
|     +-- image MIME type
|
+-- optional annotations
```

Example:

```json
{
  "type": "image",
  "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ...",
  "mimeType": "image/png"
}
```

Different providers may support different image MIME types. Provider compatibility will therefore be considered in the later image-format decision.

---

# 19. Why ImageContent Was Chosen

It avoids unnecessary infrastructure.

We do NOT need to:

- upload screenshots to public hosting
- create temporary public image URLs
- store screenshots in the database
- create a separate image-storage service
- invent a custom image representation

The intended lifecycle is:

```text
Image
  |
  v
OpenCode
  |
  v
MCP ImageContent
  |
  v
Python MCP Backend
  |
  v
Vision LLM request
  |
  v
Result
  |
  v
OpenCode
```

---

# 20. Image Persistence

## Current assumption

Images do not need to be persisted.

Intended lifecycle:

```text
Receive image
    |
Process image
    |
Send to Vision LLM
    |
Return result
    |
Discard image
```

The database is therefore not intended to contain uploaded image files in the initial design.

This is a current assumption rather than a final storage/security policy.

---

# 21. Complete End-to-End Architecture

```text
                         +-----------------------+
                         |       OpenCode        |
                         |                       |
                         |     Primary LLM       |
                         +-----------+-----------+
                                     |
                         Needs visual information
                                     |
                       +-------------+-------------+
                       |                           |
                       v                           v
                describe_image                ocr_image
                       |                           |
                       +-------------+-------------+
                                     |
                                     | MCP
                                     | ImageContent + prompt
                                     v
                         +-----------------------+
                         |    Python MCP Server  |
                         |                       |
                         | Authenticate request  |
                         |         |             |
                         | Identify user         |
                         |         |             |
                         | Active Vision Profile |
                         |         |             |
                         | System Prompt         |
                         |         |             |
                         | Compose request       |
                         +-----------+-----------+
                                     |
                                     | OpenAI-compatible
                                     | API request
                                     v
                         +-----------------------+
                         |      Vision LLM       |
                         |                       |
                         | Endpoint + Model      |
                         | + API Key             |
                         +-----------+-----------+
                                     |
                                     | Result
                                     v
                         +-----------------------+
                         |    Python MCP Server  |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         |       OpenCode        |
                         |                       |
                         |     Primary LLM       |
                         | continues reasoning   |
                         +-----------------------+
```

---

# 22. Image Description Request

```text
Primary LLM
    |
    v
describe_image(
    image = ImageContent,
    prompt = "Tell me why the application is showing this error."
)
    |
    v
MCP Server
    |
    v
Authenticated User
    |
    v
Active Vision Profile
    |
    v
Referenced System Prompt
    |
    v
Universal Extra Instructions
    |
    v
User Prompt + Image
    |
    v
OpenAI-compatible Vision LLM
    |
    v
Visual analysis result
    |
    v
MCP Server
    |
    v
OpenCode
    |
    v
Primary LLM continues reasoning
```

---

# 23. OCR Request

```text
Primary LLM
    |
    v
ocr_image(
    image = ImageContent,
    prompt = "Extract the exact error message."
)
    |
    v
MCP Server
    |
    v
Authenticated User
    |
    v
Active Vision Profile
    |
    v
Referenced System Prompt
    |
    v
User Prompt + Image
    |
    v
OpenAI-compatible Vision LLM
    |
    v
OCR result
    |
    v
MCP Server
    |
    v
OpenCode
    |
    v
Primary LLM continues reasoning
```

---

# 24. Prompt Composition Summary

| Operation | System Prompt | Universal Extra Instructions | User Prompt | Image |
|---|---|---|---|---|
| Image Description | Yes | Yes | Yes | Yes |
| OCR | Yes | No | Yes | Yes |

This behavior is **LOCKED**.

---

# 25. Locked Decisions So Far

## Decision #1 — Vision Profile configuration

**LOCKED**

Minimal fields:

```text
Name
Endpoint / Base URL
Model
API Key
System Prompt
Active status
```

Advanced parameters are deferred.

## OpenAI-compatible endpoints

**LOCKED**

Only OpenAI-compatible endpoints are supported initially.

## One active Vision Profile

**LOCKED**

Each user has exactly one active profile.

## Primary LLM cannot choose profile

**LOCKED**

The user selects the active profile.

The MCP uses it deterministically.

## Decision #2 — MCP tools

**LOCKED**

```text
describe_image(image, prompt)
ocr_image(image, prompt)
```

The backend determines behavior from the selected tool.

## Universal Extra Instructions

**LOCKED**

One global prompt.

Used only for Image Description.

Not used for OCR.

## Decision #3 — Image transmission

**LOCKED**

Use MCP `ImageContent`:

```text
type = "image"
data = base64-encoded image
mimeType = image MIME type
```

---

# 26. Not Yet Locked

## Image handling

Still to decide:

- exact supported image formats
- maximum image size
- maximum request/base64 size
- MIME validation
- unsupported-format behavior
- animated GIF handling
- image resizing/compression
- whether preprocessing is necessary
- request-size limits

## System Prompts

Still to decide:

- detailed CRUD behavior
- what happens if a referenced System Prompt is deleted
- whether referenced prompts can be edited
- validation rules
- exact frontend behavior

## Universal Extra Instructions

Still to decide:

- frontend location
- default value
- whether it can be empty
- maximum length
- update behavior

## Authentication

Still to decide:

- Google OAuth implementation
- email/password flow
- session/token mechanism
- MCP authentication mechanism
- token expiration/refresh
- user provisioning/admin script
- password hashing
- authentication middleware

The requirement that frontend and MCP access identify the same application user is established, but the implementation is not.

## Database

Still to decide:

- PostgreSQL vs MySQL
- exact schema
- indexes
- foreign keys
- UUID implementation
- migrations
- connection configuration

PostgreSQL is currently a preference/leaning, not a locked decision.

## REST API

Still to decide:

- exact endpoints
- request/response schemas
- validation
- error format
- profile CRUD
- System Prompt CRUD
- active-profile endpoint
- authentication endpoints

## MCP implementation

Still to decide:

- MCP transport
- exact authentication implementation
- Python MCP framework/library
- exact tool input schema
- exact handling of ImageContent in Python
- response/content format
- OpenCode configuration

The logical tool design and image representation are decided; these implementation details are not.

## LangChain implementation

Still to decide:

- exact LangChain packages
- exact chat model wrapper
- exact OpenAI-compatible integration
- exact image-message representation
- provider error handling

---

# 27. Initial Non-Goals

To keep the project simple, the initial version does NOT include unless later required:

```text
No autonomous vision agent
No AI-based model routing
No AI-based profile selection
No automatic fallback between vision models
No RAG
No vector database
No LangGraph
No complex agent framework
No model load balancing
No provider-specific integrations
No arbitrary model parameters
No arbitrary custom headers
No image storage service
No image history database
No unnecessary caching layer
No message queue unless required
No microservice decomposition unless required
```

---

# 28. Design Philosophy

The project follows:

> First establish exactly what the system must do. Then implement the smallest architecture that satisfies those requirements.

For every future feature:

```text
Is this required by the current requirements?
       |
       +-- YES -> design it
       |
       +-- NO  -> defer it
```

This is intentional to avoid premature complexity.

---

# 29. Current Decision Snapshot

```text
+-----------------------------------------------------+
|                 DECISION STATUS                     |
+-----------------------------------------------------+
| #1 Vision Profile configuration       LOCKED        |
|                                                     |
| Minimal profile fields                              |
| OpenAI-compatible endpoint                          |
| One active profile per user                         |
| Primary LLM cannot choose profile                   |
|                                                     |
| #2 MCP tool design                    LOCKED        |
|                                                     |
| describe_image(image, prompt)                       |
| ocr_image(image, prompt)                            |
|                                                     |
| #3 Image transmission                 LOCKED        |
|                                                     |
| MCP ImageContent                                    |
| Base64 image data + MIME type                       |
+-----------------------------------------------------+
| NEXT                                                |
|                                                     |
| #4 Image formats / size / validation               |
+-----------------------------------------------------+
```

---

# 30. Next Decision

## Decision #4 — Image Handling Rules

The next decision should determine:

1. Which image formats are supported?
2. What is the maximum image size?
3. Do we resize/compress large images?
4. Which MIME types are accepted?
5. What happens with unsupported formats?
6. Do we support animated GIFs?
7. Do we process images entirely in memory?
8. What request-size limits should apply?

Only after these are settled should we move further into implementation architecture.

---

# End of Decisions #1–#3
