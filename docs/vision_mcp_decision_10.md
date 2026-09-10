# Vision MCP — Decision #10
## Vision LLM Request & Timeout Behavior

**Status:** Locked  
**Decision:** #10  
**Scope:** How the backend constructs and executes Vision LLM requests, handles timeouts/failures, and returns results to OpenCode.

---

## 1. Project Context

The project is a lightweight Vision MCP gateway for OpenCode.

The primary LLM may not support vision, so it can call an MCP tool when it needs image understanding or OCR.

The MCP server:

1. Authenticates the OpenCode request.
2. Identifies the user from the MCP API key.
3. Loads that user's active Vision Profile.
4. Validates the supplied MCP `ImageContent`.
5. Loads the System Prompt referenced by the Vision Profile.
6. Builds a request for the configured OpenAI-compatible Vision LLM.
7. Sends the image and instructions to that model.
8. Returns the textual result to OpenCode.

The MCP server is a **vision perception sidecar/gateway**, not an autonomous agent.

---

# 2. Relevant Previous Locked Decisions

## Decision #1 — Vision Profile Configuration

Vision Profiles use minimal configuration:

- name
- endpoint/base URL
- model
- API key
- System Prompt UUID
- active flag

No temperature, max tokens, top-p, arbitrary model parameters, or custom headers initially.

Only OpenAI-compatible endpoints are supported in v1.

---

## Decision #2 — MCP Tools

Exactly two MCP tools:

```text
describe_image(image, prompt)
ocr_image(image, prompt)
```

The primary LLM chooses the operation, but **cannot choose the Vision Profile or model**.

The backend always uses the authenticated user's active Vision Profile.

---

## Decision #3 — Image Transmission

Images arrive through MCP `ImageContent`:

```text
type = "image"
data = base64-encoded image
mimeType = image MIME type
```

Images are processed directly and are not uploaded to public URLs.

---

## Decision #4 — Image Validation

Locked limits:

- Maximum encoded image size: **5 MB**
- Maximum resolution: approximately **8.3 megapixels / 4K UHD-class**

Supported:

- JPEG/JPG
- PNG
- WebP

Unsupported:

- GIF
- BMP
- TIFF
- SVG

The backend validates base64, verifies the actual image format, checks the supported format, attempts decoding, and rejects corrupted images.

No resize, compression, conversion, or cropping.

---

## Decision #5 — Error Handling

Failures are reported immediately.

There are:

- no automatic retries
- no request queue
- no provider fallback
- no multiplication of provider API calls

Clear stable errors should be returned rather than provider internals.

---

## Decision #6 — MCP Authentication

MCP uses a dedicated API key/token separate from frontend login.

Request:

```http
Authorization: Bearer <MCP_API_KEY>
```

The backend maps the key to a user UUID.

The raw key is not stored in plaintext.

---

## Decision #7 — MCP Key Provisioning

One MCP key per user initially.

The plaintext key is shown only once after generation.

OpenCode uses an environment variable:

```text
VISION_MCP_KEY=mcp_xxxxxxxxxxxxxxxxx
```

and references it in configuration:

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

---

## Decision #8 — MCP Transport

Use:

> **Remote MCP over Streamable HTTP at `/mcp`**

The MCP endpoint is part of the same Python ASGI backend as the normal API.

Example:

```text
https://your-domain.com/api/...
https://your-domain.com/mcp
```

No SSE transport for v1.

No separate MCP microservice.

HTTPS is required for deployment.

---

## Decision #9 — Rate Limiting & Concurrency

Per authenticated user:

- Maximum **20 vision calls per rolling 60 seconds**
- Maximum **3 concurrent vision calls**

Applies to both:

```text
describe_image
ocr_image
```

Limits are checked before calling the Vision provider.

If a limit is reached:

- reject immediately
- do not queue
- do not retry
- do not call the provider

The v1 limiter is in-memory.

---

# 3. Decision #10

## Vision LLM Request & Timeout Behavior

### Locked Goal

Keep Vision LLM execution simple:

```text
MCP Tool
   ↓
Authenticated User
   ↓
Active Vision Profile
   ↓
System Prompt
   +
User Prompt
   +
Optional Universal Extra Instructions
   +
Image
   ↓
LangChain
   ↓
OpenAI-Compatible Vision Endpoint
   ↓
Text Result
   ↓
MCP
   ↓
OpenCode
```

---

# 4. Request Construction

## 4.1 Image Description

For `describe_image`:

```text
Vision Profile System Prompt
        +
Universal Extra Instructions
        +
User Prompt
        +
Image
        ↓
Vision LLM
```

The Universal Extra Instructions are included only in Image Description mode.

---

## 4.2 OCR

For `ocr_image`:

```text
Vision Profile System Prompt
        +
User Prompt
        +
Image
        ↓
Vision LLM
```

Universal Extra Instructions are **not** included in OCR mode.

The user's prompt can specify how the text should be extracted or returned.

Examples:

```text
Extract all the text.

Extract the text and preserve the table structure.

Extract the error message from this screenshot.

Extract the text exactly as written.
```

---

# 5. LangChain's Scope

LangChain is deliberately used narrowly.

It is responsible for the LLM request abstraction:

```text
Our Backend
     ↓
Build messages
     ↓
ChatOpenAI
     ↓
OpenAI-Compatible Endpoint
     ↓
Vision Model
     ↓
LangChain Response
     ↓
Extract Text
```

LangChain does **not** decide:

- which Vision Profile to use
- which model to use
- OCR vs image description
- authentication
- rate limiting
- concurrency
- image validation
- database operations
- retries
- fallback providers
- autonomous actions

No LangGraph, RAG, vector database, or agent framework is required.

---

# 6. Vision Model Configuration

Conceptually, the backend will create a LangChain model using values from the authenticated user's active Vision Profile:

```text
ChatOpenAI(
    model = profile.model,
    api_key = decrypted_api_key,
    base_url = profile.endpoint,
    timeout = 60,
    max_retries = 0
)
```

The exact Python package/version and implementation syntax remain implementation details.

### Important

The Vision Profile determines:

```text
endpoint
model
API key
System Prompt
```

The primary LLM cannot override these values through MCP tool arguments.

---

# 7. OpenAI-Compatible Endpoint Scope

V1 supports OpenAI-compatible Vision endpoints only.

The backend assumes the provider can accept:

```text
text instructions
+
image input
```

and return textual model output.

We deliberately do not depend on provider-specific features.

This keeps compatibility requirements small:

```text
Text
+
Image
↓
Text
```

Provider-specific reasoning fields, tools, custom parameters, and proprietary features are deferred.

---

# 8. Image Input

The MCP `ImageContent` contains base64 image data.

The backend converts that data into the multimodal input expected by the configured Vision model.

Conceptually:

```text
MCP ImageContent
       ↓
base64 data
       +
MIME type
       ↓
Vision model image input
```

No image URL is required.

No public image hosting is required.

No image database storage is required.

---

# 9. Timeout

### Locked timeout: **60 seconds**

The Vision LLM request has a maximum duration of 60 seconds.

Flow:

```text
Request starts
     ↓
Vision provider processing
     ↓
60 seconds reached?
     │
     ├── No → wait for response
     │
     └── Yes → timeout
                  ↓
             clear error
```

Timeout error:

```text
Vision request timed out
```

No retry occurs.

---

# 10. Why 60 Seconds?

Vision requests can legitimately take longer than ordinary text requests because of:

- image processing
- OCR
- reasoning-heavy models
- slower providers
- temporary provider load

A very short timeout could reject legitimate requests.

A very long timeout could keep one of the user's limited concurrency slots occupied for too long.

60 seconds is therefore the v1 boundary.

This value can be changed later if real usage shows that a different timeout is necessary.

---

# 11. Automatic Retries

### Locked:

```text
max_retries = 0
```

There are no automatic retries.

This is required because Decision #5 already established:

> One failed Vision request should not automatically become multiple provider requests.

Example:

```text
MCP
 ↓
Vision API
 ↓
failure
 ↓
return error
```

Not:

```text
MCP
 ↓
Vision API
 ↓
failure
 ↓
retry
 ↓
failure
 ↓
retry
 ↓
failure
```

This keeps:

- API usage predictable
- latency predictable
- rate limiting predictable
- debugging simpler
- provider costs predictable

---

# 12. Successful Response Handling

The backend only needs the model's textual answer.

Conceptually:

```text
Provider Response
       ↓
LangChain AIMessage
       ↓
Extract textual content
       ↓
Return text to MCP
```

Example result:

```text
"The image shows a Python traceback originating
from line 42 in main.py..."
```

The MCP response should provide this useful textual result to the primary LLM.

---

# 13. What We Do NOT Return

The MCP response should not expose unnecessary provider internals such as:

- API keys
- raw HTTP responses
- database information
- stack traces
- internal server paths
- provider credentials
- unnecessary provider metadata

The MCP layer should return the useful Vision result or a stable error.

---

# 14. Provider Failure Translation

The backend should translate provider failures into stable application-level errors.

Conceptual mapping:

| Provider/Backend Failure | MCP Error |
|---|---|
| Invalid API key | `Vision Profile authentication failed` |
| Invalid request | `Vision request rejected` |
| Invalid endpoint/model | `Vision Profile configuration is invalid` |
| Provider 429 | `Vision service rate limit reached` |
| Provider 5xx | `Vision service temporarily unavailable` |
| Network failure | `Vision service unavailable` |
| Timeout | `Vision request timed out` |
| Invalid/unusable response | `Vision service returned invalid response` |

The exact HTTP status codes and MCP error-object structure remain implementation details.

---

# 15. No Provider Fallback

There is no fallback model or provider in v1.

If the user's active Vision Profile fails:

```text
Active Vision Profile
       ↓
Vision provider failure
       ↓
Return error
```

We do not automatically switch to another Vision Profile.

This is intentional because the user explicitly chooses their active Vision Profile.

---

# 16. No Streaming

### Locked: no Vision LLM streaming in v1.

The flow is:

```text
OpenCode
   ↓
MCP
   ↓
Vision LLM
   ↓
wait for completion
   ↓
complete textual result
   ↓
OpenCode
```

Streaming would add complexity around:

- partial responses
- cancellation
- connection handling
- error recovery
- MCP result assembly

There is no current requirement for it.

Streaming can be reconsidered later if real usage shows a benefit.

---

# 17. Complete Request Lifecycle

```text
                         OpenCode
                            │
                            │ MCP tool call
                            ▼
                    ┌────────────────┐
                    │ Authenticate   │
                    │ MCP API key    │
                    └───────┬────────┘
                            │
                            ▼
                     Identify User UUID
                            │
                            ▼
                    Check rate limit
                            │
                            ▼
                  Check concurrency limit
                            │
                            ▼
                  Load active Vision Profile
                            │
                            ▼
                   Load System Prompt
                            │
                            ▼
                      Validate Image
                            │
                            ▼
                    Decrypt API key
                            │
                            ▼
                    Build LLM request
                            │
                ┌───────────┴───────────┐
                │                       │
         describe_image             ocr_image
                │                       │
        System Prompt             System Prompt
              + User Prompt             + User Prompt
              + Extra Instructions      + Image
              + Image
                │                       │
                └───────────┬───────────┘
                            ▼
                       LangChain
                            │
                  timeout = 60 seconds
                  max_retries = 0
                            │
                            ▼
                 OpenAI-Compatible API
                            │
                            ▼
                      Vision Model
                            │
                            ▼
                    Textual Response
                            │
                            ▼
                    Return through MCP
                            │
                            ▼
                         OpenCode
                            │
                            ▼
                  Release concurrency slot
```

---

# 18. Error Lifecycle

```text
MCP Request
    ↓
Validation / Limits / Configuration
    ↓
      ┌─────────────── failure?
      │
      ├── Yes → Stable MCP error
      │
      └── No
           ↓
       Vision API
           ↓
      ┌─────────────── failure?
      │
      ├── Yes → Translate error
      │          ↓
      │       Return MCP error
      │
      └── No
           ↓
       Extract text
           ↓
       Return result
```

Regardless of success or failure:

```text
Concurrency slot
       ↓
released
```

---

# 19. Locked vs Deferred

## Locked

- Use LangChain for the LLM request abstraction.
- Use an OpenAI-compatible Vision interface.
- Use the active Vision Profile's endpoint.
- Use the active Vision Profile's model.
- Use the decrypted API key only temporarily in memory.
- Include the Vision Profile's System Prompt.
- Include Universal Extra Instructions only for Image Description.
- Do not include Universal Extra Instructions for OCR.
- Include the user's prompt.
- Convert MCP `ImageContent` into the model's multimodal image input.
- Use inline base64 image data.
- Vision request timeout: **60 seconds**.
- Automatic retries: **0**.
- Return the textual Vision result.
- Do not expose raw provider responses or secrets.
- Translate provider failures into stable application-level errors.
- No provider fallback.
- No Vision LLM streaming in v1.

## Deferred

These are implementation details rather than architectural decisions:

- Exact LangChain package/version.
- Exact exception classes to catch.
- Exact HTTP status mapping.
- Exact MCP error-object structure.
- Exact logging format.
- Exact async implementation.
- Exact backend code organization.
- Future streaming support.
- Future provider-specific adapters.
- Future configurable timeout.

---

# 20. Final Decision

### Decision #10 is LOCKED as:

> **The backend will use LangChain's OpenAI-compatible chat interface to send the authenticated user's active Vision Profile's System Prompt, the appropriate user instructions, and the MCP-provided image to the configured Vision LLM. Image Description also includes the universal Extra Instructions; OCR does not. Vision requests have a 60-second timeout and zero automatic retries. The backend returns only the useful textual result or a stable application-level error. There is no provider fallback or streaming in v1.**

---

# 21. Decision Phase Status

With Decision #10 complete, the major product and architecture requirements have been established.

```text
#1  Vision Profile configuration          LOCKED
#2  MCP tool design                       LOCKED
#3  Image transmission                    LOCKED
#4  Image validation                      LOCKED
#5  Error handling                        LOCKED
#6  MCP authentication                    LOCKED
#7  MCP key provisioning                  LOCKED
#8  MCP transport                         LOCKED
#9  Rate limiting & concurrency           LOCKED
#10 Vision request & timeout behavior     LOCKED
```

The next phase should be:

> **Architecture & Implementation Design**

This should translate the locked requirements into:

- backend architecture
- frontend structure
- database schema
- API routes
- MCP implementation
- authentication flow
- project directory structure
- deployment shape
- implementation order

No additional decisions should be added unless a genuine unresolved requirement appears during architecture/design.
