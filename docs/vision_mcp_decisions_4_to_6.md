# Vision MCP Project — Decisions #4 to #6

This document captures the requirements, reasoning, assumptions, locked decisions, and intentionally deferred items agreed for Decisions #4, #5, and #6.

## 1. Project Context

The project is a Python backend + TypeScript frontend service acting as a **vision sidecar / visual perception gateway** for OpenCode and similar MCP-capable coding agents.

The primary LLM remains responsible for reasoning. When it needs visual information, it invokes one of two MCP tools:

- `describe_image(image, prompt)`
- `ocr_image(image, prompt)`

The MCP backend authenticates the caller, identifies the user, loads that user's active Vision Profile, and sends the image plus the appropriate prompt composition to the configured OpenAI-compatible vision model.

The project is intentionally simple initially. No unnecessary agents, LangGraph, RAG, vector database, automatic retries, or provider-specific integrations are being added unless later requirements justify them.

## 2. Existing Constraints Relevant to #4–#6

### Vision Profiles

Each user can configure Vision Profiles containing, conceptually:

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

There is exactly **one active Vision Profile per user**.

MCP tool arguments do not contain profile ID, model, endpoint, or API key. The backend deterministically uses the authenticated user's active Vision Profile.

### User isolation

All user-owned resources are scoped to the authenticated user's UUID. A caller cannot simply supply another user's UUID to access their configuration.

### Vision API

Only **OpenAI-compatible endpoints** are supported initially.

### Image transport

Images use MCP `ImageContent`:

```text
type = "image"
data = base64-encoded image data
mimeType = image MIME type
```

No image URL, public hosting, or custom image transport is required.

### Initial usage limits

The initial deployment is **not horizontally scaled**.

Per user:

- Maximum **3 concurrent vision calls**
- Maximum **20 vision calls per minute**

These limits may be revisited if the system later scales.

---

# Decision #4 — Image Handling & Validation

## 4.1 Purpose

Decision #4 defines what the backend does with an image before sending it to the Vision LLM.

The goal is to accept normal supported images while preventing invalid, unsupported, or excessively large inputs from reaching the provider.

The initial implementation should not perform unnecessary image processing.

## 4.2 Maximum encoded image size

### LOCKED

**Maximum image size: 5 MB.**

The backend checks the incoming encoded image data against the 5 MB limit.

A compressed 5 MB image does not necessarily consume only 5 MB of RAM after decoding. Therefore, the size limit and resolution limit protect against different resource costs.

## 4.3 Supported image formats

### LOCKED

| Format | Status |
|---|---|
| JPEG / JPG | Supported |
| PNG | Supported |
| WebP | Supported |
| GIF | Not supported |
| BMP | Not supported |
| TIFF | Not supported |
| SVG | Not supported |

GIF was explicitly rejected for the initial implementation.

## 4.4 Image validation

### LOCKED

The backend validates the image before sending it to the Vision LLM.

Validation consists of:

1. Validate the base64 data.
2. Enforce the 5 MB maximum.
3. Verify the actual image format rather than trusting only the declared MIME type.
4. Verify that the format is supported.
5. Attempt to decode the image.
6. Reject corrupted or invalid images.
7. Reject unsupported formats.
8. Do not resize, compress, convert, or otherwise modify the image.

### Validation flow

```text
MCP ImageContent
       |
       v
Validate base64
       |
       v
Check encoded size <= 5 MB
       |
       v
Inspect actual image format
       |
       v
Supported format?
     /          No         Yes
   |           |
 Reject        v
          Decode image
               |
          Decode successful?
             /                  No         Yes
           |           |
         Reject        v
                 Check resolution
                       |
                       v
                  Send to LLM
```

The declared `mimeType` is metadata, not proof that the bytes actually represent that image type.

## 4.5 Maximum resolution

### LOCKED

Maximum image resolution is approximately **8.3 megapixels**, corresponding to 4K UHD-class resolution.

The preferred rule is based on **total pixel count**, not a strict 3840 × 2160 width/height requirement.

Examples:

| Dimensions | Approx. pixels | Result |
|---|---:|---|
| 1920 × 1080 | 2.07 MP | Accept |
| 2560 × 1440 | 3.69 MP | Accept |
| 3840 × 2160 | 8.29 MP | Accept |
| 4000 × 2000 | 8.00 MP | Accept |
| 5120 × 1440 | 7.37 MP | Accept |
| 7680 × 4320 | 33.18 MP | Reject |

A panoramic image can therefore be accepted if its total pixel count remains within the limit.

## 4.6 What happens above the resolution limit?

Images above the resolution limit are rejected.

Conceptual error:

```text
Image exceeds the maximum supported resolution of 8.3 megapixels.
```

The initial implementation does **not** automatically resize the image.

## 4.7 No automatic image modification

### LOCKED

The backend does not automatically:

- resize
- compress
- convert formats
- crop
- alter quality
- otherwise modify the image

This keeps behavior predictable and the first implementation simple.

## 4.8 Memory considerations

A 5 MB encoded image is not necessarily a 5 MB RAM workload.

For RGBA data:

```text
raw pixel memory ≈ width × height × 4 bytes
```

Approximate examples:

| Resolution | Approx. raw RGBA memory |
|---|---:|
| 1920 × 1080 | ~8 MB |
| 3840 × 2160 | ~32 MB |
| 7680 × 4320 | ~127 MB |
| 10000 × 10000 | ~381 MB |

Actual process memory can be higher because of the decoder, intermediate buffers, Python/runtime overhead, request handling, and provider request construction.

The 8.3 MP limit prevents very high-resolution images from being decoded even when compression allows them to fit under the 5 MB encoded-size limit.

The system also limits each user to 3 concurrent calls, bounding per-user concurrency in the initial deployment.

## 4.9 Image lifecycle

### CURRENT ASSUMPTION

Images do not need to be persisted.

Intended lifecycle:

```text
Receive ImageContent
       |
       v
Validate
       |
       v
Decode / prepare
       |
       v
Send to Vision LLM
       |
       v
Return result
       |
       v
Discard image
```

No database image storage is required by current requirements.

This is an assumption rather than a separately finalized storage/security policy.

## Decision #4 Summary

### LOCKED

- 5 MB maximum encoded image size.
- ~8.3 MP maximum resolution.
- JPEG/JPG supported.
- PNG supported.
- WebP supported.
- GIF rejected.
- BMP rejected.
- TIFF rejected.
- SVG rejected.
- Base64 validation.
- Actual image validation rather than trusting MIME type alone.
- Successful decoding required.
- Corrupt/invalid images rejected.
- Unsupported formats rejected.
- No resizing.
- No compression.
- No format conversion.

### NOT YET LOCKED

- Exact image decoding library.
- Exact error-code taxonomy.
- Exact MCP error response structure.
- Whether images should ever be persisted.
- Any future changes to image limits.

---

# Decision #5 — Error Handling & Failure Behavior

## 5.1 Goal

The MCP server can fail at multiple points:

```text
OpenCode
   |
   v
MCP request
   |
   +--> Image validation failure
   |
   +--> Authentication failure
   |
   +--> User/profile configuration failure
   |
   +--> API key/decryption failure
   |
   +--> Vision provider timeout
   |
   +--> Vision provider API failure
   |
   +--> Unexpected provider response
```

The system needs predictable failure behavior.

## 5.2 Retry policy

### LOCKED — Option A

**MCP returns a clear error immediately.**

There are **no automatic retries** in the initial implementation.

If the Vision provider times out or returns an error, the backend reports the failure instead of automatically issuing another request.

Reasons for avoiding automatic retries initially:

- Prevent multiplying provider API calls.
- Keep latency predictable.
- Keep rate limiting simple.
- Make failures easier to debug.
- Avoid unexpected provider costs.

Retries can be added later if actual provider behavior creates a concrete need.

## 5.3 Expected error categories

| Failure | MCP should communicate |
|---|---|
| Invalid base64 | Image data is invalid |
| Unsupported format | Image format is unsupported |
| >5 MB | Image exceeds the size limit |
| >8.3 MP | Image resolution exceeds the limit |
| No active Vision Profile | No active Vision Profile is configured |
| Vision API authentication failure | Vision Profile authentication failed |
| Provider unavailable | Vision service is temporarily unavailable |
| Provider timeout | Vision request timed out |
| Per-user rate limit reached | Vision call rate limit reached |
| Concurrency limit reached | Too many concurrent vision calls |
| Unexpected provider response | Vision service returned an invalid response |

These are conceptual messages. Exact HTTP/MCP error codes and response schemas are not yet locked.

## 5.4 Do not expose secrets or internal implementation details

Errors must not reveal:

- decrypted API keys
- API key values
- database credentials
- internal secret values
- unnecessary stack traces
- sensitive provider request data
- unnecessary database internals

Good:

```text
Vision request timed out.
```

Bad:

```text
requests.exceptions.ReadTimeout:
HTTPSConnectionPool(...)
```

Internal details may be retained in controlled server-side logs when appropriate, but logs must also never contain API keys.

## 5.5 Error flow

```text
                   MCP Request
                       |
                       v
                 Authenticate
                       |
                       v
                 Validate image
                       |
              +--------+--------+
              |                 |
            Fail              Pass
              |                 |
              v                 v
        Return clear       Load active
            error             profile
                                |
                                v
                         Call Vision LLM
                                |
                    +-----------+-----------+
                    |                       |
                  Fail                    Success
                    |                       |
                    v                       v
             Return clear              Return result
                 error
```

There is intentionally no automatic retry branch.

## Decision #5 Summary

### LOCKED

- Immediate clear error on failure.
- No automatic provider retries.
- Do not expose secrets.
- Do not expose unnecessary internal stack traces/details.
- Errors should be understandable to the primary LLM.

### NOT YET LOCKED

- Exact HTTP status codes.
- Exact MCP error object structure.
- Exact machine-readable error codes/names.
- Detailed server-side logging policy.
- Whether errors need different representations for the primary LLM versus end user.

---

# Decision #6 — Authentication & MCP Identity

## 6.1 Problem

The backend must know which user is making each MCP request.

This is required because it must load the correct:

- active Vision Profile
- System Prompt
- encrypted Vision API key
- endpoint
- model

Example:

```text
User A
  |
  +--> Vision Profile A
  +--> System Prompt A
  +--> API key A

User B
  |
  +--> Vision Profile B
  +--> System Prompt B
  +--> API key B
```

The MCP request must not simply supply another user's UUID and thereby access their configuration.

## 6.2 Authentication vs authorization

### Authentication

Answers:

> Who are you?

```text
MCP key
   |
   v
Backend
   |
   v
User A
```

### Authorization

Answers:

> What can that user access?

```text
User A
   |
   v
User A's active Vision Profile
```

The backend must never load User B's resources for an authenticated User A.

## 6.3 Context7 research

Context7 was checked because it is a real remote MCP service used with coding agents.

Current Context7 documentation shows remote MCP authentication using API keys in a Bearer authorization header:

```http
Authorization: Bearer YOUR_API_KEY
```

Context7 documents this approach for OpenCode and Codex remote MCP configurations. Context7 also supports OAuth for MCP clients implementing MCP OAuth, but OAuth is not required for the simpler API-key setup.

Context7's documented OpenCode remote configuration uses a remote MCP URL and an Authorization header. Its Codex documentation similarly shows remote MCP authentication through an HTTP Authorization header.

This validates that a dedicated bearer-style MCP key is a normal pattern for remote MCP clients.

## 6.4 Chosen authentication model

### LOCKED

Use a **dedicated MCP API key/token** for MCP authentication.

The MCP key is separate from the user's normal frontend login/session.

Conceptually:

```text
                  Frontend
                     |
              User authenticates
              Google / email-password
                     |
                     v
                User account
                     |
             Generate MCP key
                     |
                     v
              mcp_xxxxxxxxx
                     |
                     | configured in OpenCode
                     v
                  OpenCode
                     |
       Authorization: Bearer <MCP key>
                     |
                     v
                Vision MCP
                     |
                Authenticate
                     |
                     v
                 User UUID
                     |
                     v
          User's active Vision Profile
```

## 6.5 Why separate MCP authentication from frontend login?

OpenCode is an MCP client. It does not need to participate directly in the project's website login flow.

Trying to make OpenCode reuse a normal web session would unnecessarily couple frontend authentication and MCP authentication.

Instead:

```text
Website
   |
   +--> normal authentication

OpenCode
   |
   +--> MCP API key
```

The backend maps the MCP key to the same user account.

## 6.6 MCP request authentication

Intended request model:

```http
Authorization: Bearer <MCP_API_KEY>
```

Tool arguments remain focused on the operation:

```text
describe_image(image, prompt)
```

or:

```text
ocr_image(image, prompt)
```

The primary LLM does not supply:

```text
user_id
profile_id
model
endpoint
api_key
```

This prevents the LLM from selecting another user's configuration.

## 6.7 MCP key storage

### LOCKED DESIGN DIRECTION

The raw MCP key should **not** be stored as plaintext in the database.

Conceptually:

```text
MCP key generated
       |
       +----> shown to user / configured in OpenCode
       |
       v
Hash
       |
       v
Database
```

A conceptual database record can contain:

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

The exact table/schema is not finalized.

### Why hash it?

If someone obtains only the database contents, they should not immediately have the usable MCP credential.

## 6.8 Key lifecycle

```text
Generate
   |
   v
Show key to user
   |
   v
User configures OpenCode
   |
   v
OpenCode sends key
   |
   v
Backend verifies key
   |
   v
Request allowed
```

If compromised:

```text
Revoke old key
      |
      v
Old key no longer works
      |
      v
Generate new key
      |
      v
Configure new key in OpenCode
```

## 6.9 One key per user vs multiple keys

Multiple keys were considered:

```text
User A
 ├── Desktop key
 ├── Laptop key
 └── Server key
```

This gives independent revocation but adds complexity.

### LOCKED

**One dedicated MCP key per user initially.**

Multiple independently revocable keys are deferred until there is a real need.

## 6.10 OAuth

OAuth was considered because Context7 supports it for remote MCP connections and modern MCP clients can support MCP OAuth.

However, implementing OAuth would add:

- authorization flow
- browser interaction
- token issuance
- token refresh
- client registration/configuration
- OAuth discovery/endpoints
- additional state management

### LOCKED

**No MCP OAuth initially.**

OAuth can be introduced later if a concrete need appears.

## 6.11 Authentication flow

```text
                  +------------------+
                  |     OpenCode     |
                  +--------+---------+
                           |
                           | MCP request
                           | Authorization: Bearer <key>
                           v
                  +------------------+
                  |   Vision MCP     |
                  +--------+---------+
                           |
                           | Verify MCP key
                           v
                  +------------------+
                  |    User UUID     |
                  +--------+---------+
                           |
                           | Load resources
                           v
             +----------------------------+
             | User's active Vision       |
             | Profile                    |
             +-------------+--------------+
                           |
                           v
                   Vision LLM request
```

The MCP key determines identity. The backend then determines authorization based on that identity.

## 6.12 End-to-end request with current decisions

```text
OpenCode
   |
   | MCP ImageContent
   | + prompt
   | + Bearer MCP key
   v
Vision MCP
   |
   | Authenticate key
   v
User UUID
   |
   | Load active profile
   v
Vision Profile
   |
   +--> endpoint
   +--> model
   +--> encrypted API key
   +--> system prompt UUID
   |
   v
Validate image
   |
   +--> base64 valid?
   +--> <= 5 MB?
   +--> JPEG/PNG/WebP?
   +--> decodable?
   +--> <= 8.3 MP?
   |
   v
Construct vision request
   |
   | Image Description mode:
   | System Prompt
   | + Universal Extra Instructions
   | + User Prompt
   | + Image
   v
OpenAI-compatible Vision LLM
   |
   +--> failure → immediate clear error
   |
   v
Vision result
   |
   v
Return result to OpenCode
   |
   v
Discard image
```

For `ocr_image`:

```text
System Prompt
+
User Prompt
+
Image
```

The Universal Extra Instructions are not used in OCR mode.

## 6.13 Rate limiting and authentication

Authentication provides the user identity.

That identity is then used for the existing per-user limits:

```text
User UUID
   |
   +--> max 3 concurrent vision calls
   |
   +--> max 20 calls/minute
```

Therefore, a caller cannot bypass limits by supplying another user ID in tool arguments.

## Decision #6 Summary

### LOCKED

- MCP uses a dedicated API key/token.
- The key is separate from frontend login/session authentication.
- MCP requests use Bearer authentication.
- Backend maps the MCP key to a user UUID.
- User identity is derived from authentication.
- Tool arguments do not include user ID/profile ID/API key/model/endpoint.
- One MCP key per user initially.
- Raw MCP keys are not stored in plaintext; store a hash.
- Key can be revoked/regenerated.
- No MCP OAuth initially.
- Per-user rate/concurrency limits are associated with authenticated identity.

### NOT YET LOCKED

- Exact MCP key format/prefix.
- Exact key generation method/library.
- Exact hash algorithm and implementation.
- Exact MCP credential database schema.
- Exact frontend UI for creating/revoking the key.
- Exact OpenCode configuration/setup instructions.
- Whether `last_used_at` should be stored.
- Exact token expiration policy.
- Exact API/MCP error response structure.
- Whether future versions should support multiple MCP keys per user.

---

# 3. Current Locked Decisions Snapshot

| Decision | Status | Current choice |
|---|---|---|
| #4 Image handling | Locked | 5 MB, ~8.3 MP, JPEG/PNG/WebP, validation, no modification |
| #5 Error handling | Locked | Immediate clear errors, no automatic retries |
| #6 MCP authentication | Locked | Dedicated bearer-style MCP API key, one per user initially |

---

# 4. Important Assumptions

1. Images are processed in memory and discarded after the request.
2. The exact image decoding library has not been selected.
3. The exact database schema for MCP credentials has not been finalized.
4. The exact token-generation/hash implementation has not been finalized.
5. The exact MCP error schema has not been finalized.
6. The exact frontend flow for generating/revoking MCP credentials has not been finalized.
7. The initial deployment is not horizontally scaled.
8. Per user: maximum 3 concurrent vision calls and 20 calls/minute.
9. OpenAI-compatible APIs remain the only supported Vision LLM integration type initially.

---

# 5. Deliberately Deferred Complexity

The following are intentionally not being added at this stage:

- MCP OAuth
- Multiple MCP credentials per user
- Automatic Vision LLM retries
- Automatic image resizing
- Automatic image compression
- Automatic format conversion
- GIF support
- Arbitrary image formats
- Image persistence
- Complex API gateway infrastructure
- Horizontal scaling
- Advanced abuse detection
- Provider-specific authentication adapters
- Complex token/session architecture

Guiding principle:

> If a feature is not required by the current requirements, defer it.

---

# 6. Next Decision

## Decision #7 — MCP Key Provisioning & OpenCode Configuration

This should answer:

- How the user generates their MCP key.
- Where they see it.
- Whether it is shown once.
- How they configure it in OpenCode.
- Whether the backend provides a copy/paste configuration snippet.
- What happens when the key is revoked/regenerated.
- Whether environment variables should be recommended.
- How to avoid accidentally committing the MCP key into a project repository.

No implementation decision for #7 has been made yet.
