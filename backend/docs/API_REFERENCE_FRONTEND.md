# ContextHub Frontend API Reference Manual

> **Version:** 1.0.0  
> **Target Audience:** Frontend Developers (Next.js / React / TypeScript)  
> **Base URL:** `/api/v1`  
> **Content-Type:** `application/json` (unless specifying `multipart/form-data` for file uploads or `text/event-stream` for SSE streaming)

---

## 1. Global Concepts & Protocols

### 1.1 Authentication & Multi-Tenancy Headers

ContextHub utilizes JWT Bearer Tokens for authentication and single-tenant multi-tenant isolation.

| Header | Required For | Format / Value | Description |
| :--- | :--- | :--- | :--- |
| `Authorization` | All authenticated endpoints | `Bearer <access_token>` | Issued upon `/auth/login`, `/auth/refresh`, or `/auth/invitations/accept`. |
| `X-Tenant-Slug` | `POST /auth/login` | `string` (e.g. `acme-corp`) | Tenant organization identifier slug. |

### 1.2 Pagination Standard (`CursorPage[T]`)

All list endpoints use key-set **Cursor Pagination** for performance and pagination consistency.

#### Request Query Parameters
* `cursor` (`string`, optional): Opaque token returned in the previous response's `next_cursor` field. Omit for the first page.
* `limit` (`integer`, optional, default: `20`, range: `1` to `100`): Maximum number of items to return.

#### Response Envelope TypeScript Interface
```typescript
interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}
```

### 1.3 Standard Error Format

All REST API errors return a standard JSON payload:

```typescript
// Standard HTTP 400, 401, 403, 404, 409, 500 Error
interface ApiError {
  detail: string;
}

// Validation Error (HTTP 422 Unprocessable Entity)
interface ValidationError {
  detail: string;
  errors: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}
```

---

## 2. Auth Module (`/api/v1/auth`)

### 2.1 Public Authentication Endpoints

#### `POST /api/v1/auth/register`
Creates a new tenant organization and registers its first Administrator user.

* **Auth required:** No
* **Request Body:**
```json
{
  "tenant_name": "Acme Organization",
  "email": "admin@acme.com",
  "password": "SecurePassword123!"
}
```
* **Response (201 Created):** `UserResponse`
```json
{
  "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "email": "admin@acme.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-08-08T15:00:00Z",
  "updated_at": "2026-08-08T15:00:00Z"
}
```

---

#### `POST /api/v1/auth/login`
Authenticates a user for a specific tenant and returns an access/refresh token pair.

* **Auth required:** No
* **Headers:** `X-Tenant-Slug: acme-organization`
* **Request Body:**
```json
{
  "email": "admin@acme.com",
  "password": "SecurePassword123!"
}
```
* **Response (200 OK):** `TokenResponse`
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

---

#### `POST /api/v1/auth/refresh`
Exchanges a valid refresh token for a brand new access and refresh token pair.

* **Auth required:** No
* **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
* **Response (200 OK):** `TokenResponse`

---

#### `POST /api/v1/auth/invitations/accept`
Allows an invited user to accept an invitation token and complete account creation.

* **Auth required:** No
* **Request Body:**
```json
{
  "invite_token": "eyJhbGciOi...",
  "email": "member@acme.com",
  "password": "MemberPassword123!"
}
```
* **Response (201 Created):** `UserResponse`

---

### 2.2 Authenticated Session Endpoints

#### `POST /api/v1/auth/logout`
Revokes an active refresh token session.

* **Auth required:** Yes (`Bearer <access_token>`)
* **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
* **Response (204 No Content):** (Empty payload)

---

#### `POST /api/v1/auth/logout-all`
Revokes all active refresh token sessions across all devices for the current user.

* **Auth required:** Yes
* **Request Body:** None
* **Response (204 No Content):** (Empty payload)

---

### 2.3 User Management Endpoints

#### `GET /api/v1/auth/me`
Retrieves the profile of the currently authenticated user.

* **Auth required:** Yes
* **Response (200 OK):** `UserResponse`

---

#### `PUT /api/v1/auth/users/me/password`
Updates the password for the active authenticated user. Automatically revokes all existing sessions.

* **Auth required:** Yes
* **Request Body:**
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!"
}
```
* **Response (204 No Content):** (Empty payload)

---

#### `GET /api/v1/auth/users`
Lists all users within the current tenant organization.

* **Auth required:** Yes
* **Query Parameters:** `cursor`, `limit`, `is_active` (`boolean`, optional)
* **Response (200 OK):** `CursorPage<UserResponse>`

---

#### `PATCH /api/v1/auth/users/{user_id}/role`
Updates a user's role. Enforces role hierarchy rules (e.g. Admins cannot demote themselves or modify higher/equal privilege users).

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `user_id` (`UUID`)
* **Request Body:**
```json
{
  "role": "admin" // Options: "owner" | "admin" | "member" | "viewer"
}
```
* **Response (200 OK):** `UserResponse`

---

#### `POST /api/v1/auth/users/{user_id}/deactivate`
Deactivates a user's account and revokes all active token sessions.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `user_id` (`UUID`)
* **Response (204 No Content):** (Empty payload)

---

#### `POST /api/v1/auth/users/{user_id}/reactivate`
Reactivates a deactivated user's account.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `user_id` (`UUID`)
* **Response (204 No Content):** (Empty payload)

---

### 2.4 Invitation Management Endpoints

#### `POST /api/v1/auth/invitations`
Creates a new email invitation to join the tenant organization.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Request Body:**
```json
{
  "email": "newmember@acme.com",
  "role": "member" // Default: "member"
}
```
* **Response (200 OK):** `InvitationCreateResponse`
```json
{
  "invitation": {
    "id": "e305e94b-7411-4f10-b998-3564c7ad3db3",
    "email": "newmember@acme.com",
    "role": "member",
    "status": "pending", // "pending" | "accepted" | "expired" | "revoked"
    "expires_at": "2026-08-15T15:00:00Z",
    "created_at": "2026-08-08T15:00:00Z"
  },
  "invite_token": "eyJhbGciOi..."
}
```

---

#### `GET /api/v1/auth/invitations`
Lists invitations sent by the tenant organization.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Query Parameters:** `cursor`, `limit`, `status` (`pending`, `accepted`, `expired`, `revoked`)
* **Response (200 OK):** `CursorPage<InvitationResponse>`

---

#### `POST /api/v1/auth/invitations/{invitation_id}/revoke`
Revokes a pending invitation.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `invitation_id` (`UUID`)
* **Response (204 No Content):** (Empty payload)

---

#### `POST /api/v1/auth/invitations/{invitation_id}/resend`
Regenerates an invitation token and extends the expiry date by 7 days.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `invitation_id` (`UUID`)
* **Response (200 OK):** `InvitationCreateResponse`

---

## 3. Workspaces Module (`/api/v1/workspaces`)

Workspaces group documents and chat sessions within a tenant.

#### `POST /api/v1/workspaces`
Creates a new workspace.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Request Body:**
```json
{
  "name": "Engineering KB",
  "slug": "engineering-kb", // Optional, auto-generated from name if omitted
  "description": "Technical documentation and architecture specs" // Optional
}
```
* **Response (201 Created):** `WorkspaceResponse`
```json
{
  "id": "a823c921-995a-4e20-8e12-00569a84ef3b",
  "name": "Engineering KB",
  "slug": "engineering-kb",
  "description": "Technical documentation and architecture specs",
  "is_active": true,
  "dlp_rules": null,
  "created_at": "2026-08-08T15:00:00Z",
  "updated_at": "2026-08-08T15:00:00Z"
}
```

---

#### `GET /api/v1/workspaces`
Lists active workspaces for the current tenant.

* **Auth required:** Yes
* **Query Parameters:** `cursor`, `limit`
* **Response (200 OK):** `CursorPage<WorkspaceResponse>`

---

#### `GET /api/v1/workspaces/{workspace_id}`
Retrieves a single workspace by ID.

* **Auth required:** Yes
* **Path Parameters:** `workspace_id` (`UUID`)
* **Response (200 OK):** `WorkspaceResponse`

---

#### `PATCH /api/v1/workspaces/{workspace_id}`
Updates details of an existing workspace.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `workspace_id` (`UUID`)
* **Request Body:**
```json
{
  "name": "Engineering Knowledge Base",
  "description": "Updated description",
  "is_active": true
}
```
* **Response (200 OK):** `WorkspaceResponse`

---

## 4. Documents Module (`/api/v1/documents`)

### 4.1 File Formats & Limits
* **Supported Extensions:** `.pdf`, `.docx`, `.md`, `.txt`, `.csv`, `.json`
* **Max File Size:** `50 MB` (HTTP 413 error if exceeded)

---

#### `POST /api/v1/documents/upload/{workspace_id}`
Uploads a file to a workspace and triggers the background ingestion pipeline (Parsing $\to$ DLP Masking $\to$ Chunking $\to$ Embedding $\to$ Search Indexing).

* **Auth required:** Yes
* **Content-Type:** `multipart/form-data`
* **Path Parameters:** `workspace_id` (`UUID`)
* **Form Data:**
  * `file`: File blob/stream
* **Response (201 Created):** `DocumentUploadResponse`
```json
{
  "document": {
    "id": "f512c12a-89a1-4389-9a21-998811aa22bb",
    "workspace_id": "a823c921-995a-4e20-8e12-00569a84ef3b",
    "filename": "architecture.pdf",
    "mime_type": "application/pdf",
    "file_size": 204800,
    "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "version": 1,
    "status": "pending", // DocumentStatus: "pending" | "processing" | "active" | "error"
    "error_message": null,
    "created_at": "2026-08-08T15:00:00Z",
    "updated_at": "2026-08-08T15:00:00Z"
  },
  "message": "Document uploaded and queued for processing."
}
```

---

#### `GET /api/v1/documents/workspace/{workspace_id}`
Lists documents belonging to a specific workspace.

* **Auth required:** Yes
* **Path Parameters:** `workspace_id` (`UUID`)
* **Query Parameters:** `cursor`, `limit`
* **Response (200 OK):** `CursorPage<DocumentResponse>`

---

#### `GET /api/v1/documents/{document_id}`
Retrieves document status and metadata by ID.

* **Auth required:** Yes
* **Path Parameters:** `document_id` (`UUID`)
* **Response (200 OK):** `DocumentResponse`

---

#### `POST /api/v1/documents/{document_id}/reingest`
Uploads a replacement file for an existing document, incrementing the version counter and re-running ingestion.

* **Auth required:** Yes
* **Content-Type:** `multipart/form-data`
* **Path Parameters:** `document_id` (`UUID`)
* **Form Data:**
  * `file`: File blob/stream
* **Response (200 OK):** `DocumentUploadResponse`

---

#### `DELETE /api/v1/documents/{document_id}`
Deletes a document, its raw files from S3/storage, and all vector chunks from the database.

* **Auth required:** Yes (Requires `admin` or `owner` role)
* **Path Parameters:** `document_id` (`UUID`)
* **Response (204 No Content):** (Empty payload)

---

## 5. Chat & RAG Module (`/api/v1/chat`)

### 5.1 Server-Sent Events (SSE) Streaming Interface

#### `POST /api/v1/chat/stream`
Streams grounded RAG responses, token updates, and citation markers via SSE.

* **Auth required:** Yes
* **Content-Type:** `application/json`
* **Accept:** `text/event-stream`
* **Rate Limits:** 10 req/min (Standard), 30 req/min (Pro), 60 req/min (Enterprise)
* **Request Body:**
```json
{
  "workspace_id": "a823c921-995a-4e20-8e12-00569a84ef3b",
  "session_id": "c711a88b-2121-4999-88ab-7733221100aa", // Optional: null to create a new session
  "message": "What are our high availability targets for Q4?",
  "model": null, // Optional custom model string override
  "document_ids": ["f512c12a-89a1-4389-9a21-998811aa22bb"] // Optional document filtering list
}
```

#### Event Sequence Format (`text/event-stream`)
The server responds with a sequence of formatted SSE frames: `data: <JSON_STRING>\n\n`.

1. **`session` Event (Dispatched first)**
   ```json
   data: {"type": "session", "data": {"session_id": "c711a88b-2121-4999-88ab-7733221100aa", "title": "HA Targets", "workspace_id": "a823c921-995a-4e20-8e12-00569a84ef3b"}}
   ```
2. **`citations` Event (Retrieved context sources)**
   ```json
   data: {"type": "citations", "data": [{"index": 1, "document_id": "f512c12a...", "document_name": "architecture.pdf", "chunk_id": "b11...", "content_excerpt": "Our target SLA is 99.99%...", "page_numbers": [4], "confidence": 0.94}]}
   ```
3. **`token` Event (Repeated for streamed text chunks)**
   ```json
   data: {"type": "token", "data": {"text": "According to the architecture specifications "}}
   ```
   ```json
   data: {"type": "token", "data": {"text": "[^1], the high availability target is 99.99%."}}
   ```
4. **`done` Event (Synthesis completed)**
   ```json
   data: {"type": "done", "data": {"full_text": "According to the architecture specifications [^1], the high availability target is 99.99%.", "usage": {"prompt_tokens": 512, "completion_tokens": 28, "total_tokens": 540, "cost_usd": 0.0002}}}
   ```
5. **Stream Termination Marker**
   ```text
   data: [DONE]
   ```
6. **`error` Event (Dispatched if exception occurs)**
   ```json
   data: {"type": "error", "data": {"message": "Workspace missing or inactive"}}
   ```

---

### 5.2 Next.js / React SSE Client Integration Code Example

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source';

export async function streamChatResponse({
  token,
  requestPayload,
  onSession,
  onCitations,
  onToken,
  onDone,
  onError,
}: {
  token: string;
  requestPayload: {
    workspace_id: string;
    session_id?: string | null;
    message: string;
    document_ids?: string[] | null;
  };
  onSession: (sessionData: any) => void;
  onCitations: (citations: any[]) => void;
  onToken: (text: string) => void;
  onDone: (summary: any) => void;
  onError: (err: string) => void;
}) {
  await fetchEventSource('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(requestPayload),
    onmessage(ev) {
      if (ev.data === '[DONE]') return;
      
      try {
        const payload = JSON.parse(ev.data);
        switch (payload.type) {
          case 'session':
            onSession(payload.data);
            break;
          case 'citations':
            onCitations(payload.data);
            break;
          case 'token':
            onToken(payload.data.text);
            break;
          case 'done':
            onDone(payload.data);
            break;
          case 'error':
            onError(payload.data.message);
            break;
        }
      } catch (err) {
        console.error('Failed to parse SSE payload', err);
      }
    },
    onerror(err) {
      onError(err.message || 'Stream connection failed');
    },
  });
}
```

---

### 5.3 Chat Session Management Endpoints

#### `POST /api/v1/chat/sessions`
Manually creates a new chat session.

* **Auth required:** Yes
* **Request Body:**
```json
{
  "workspace_id": "a823c921-995a-4e20-8e12-00569a84ef3b",
  "title": "Q4 Planning" // Optional, default: "New Conversation"
}
```
* **Response (201 Created):** `ChatSessionResponse`
```json
{
  "id": "c711a88b-2121-4999-88ab-7733221100aa",
  "workspace_id": "a823c921-995a-4e20-8e12-00569a84ef3b",
  "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "title": "Q4 Planning",
  "running_summary": null,
  "message_count": 0,
  "total_tokens": 0,
  "total_cost_usd": 0.0,
  "created_at": "2026-08-08T15:00:00Z",
  "updated_at": "2026-08-08T15:00:00Z"
}
```

---

#### `GET /api/v1/chat/sessions/workspace/{workspace_id}`
Lists all chat sessions created by the current user within a specific workspace.

* **Auth required:** Yes
* **Path Parameters:** `workspace_id` (`UUID`)
* **Query Parameters:** `cursor`, `limit`
* **Response (200 OK):** `CursorPage<ChatSessionResponse>`

---

#### `GET /api/v1/chat/sessions/{session_id}`
Retrieves a single chat session by ID.

* **Auth required:** Yes
* **Path Parameters:** `session_id` (`UUID`)
* **Response (200 OK):** `ChatSessionResponse`

---

#### `PATCH /api/v1/chat/sessions/{session_id}`
Updates the title of a chat session.

* **Auth required:** Yes
* **Path Parameters:** `session_id` (`UUID`)
* **Request Body:**
```json
{
  "title": "Updated Session Title"
}
```
* **Response (200 OK):** `ChatSessionResponse`

---

#### `DELETE /api/v1/chat/sessions/{session_id}`
Deletes a chat session and all messages contained in its history.

* **Auth required:** Yes
* **Path Parameters:** `session_id` (`UUID`)
* **Response (204 No Content):** (Empty payload)

---

### 5.4 Messages & Feedback Endpoints

#### `GET /api/v1/chat/sessions/{session_id}/messages`
Lists the message history for a chat session in ascending chronological order.

* **Auth required:** Yes
* **Path Parameters:** `session_id` (`UUID`)
* **Query Parameters:** `cursor`, `limit`
* **Response (200 OK):** `CursorPage<ChatMessageResponse>`
```json
{
  "items": [
    {
      "id": "11111111-2222-3333-4444-555555555555",
      "session_id": "c711a88b-2121-4999-88ab-7733221100aa",
      "role": "user", // "user" | "assistant"
      "content": "What are our high availability targets for Q4?",
      "citations": null,
      "confidence_score": null,
      "token_count": 12,
      "cost_usd": 0.0,
      "feedback": null,
      "feedback_note": null,
      "created_at": "2026-08-08T15:00:00Z"
    },
    {
      "id": "66666666-7777-8888-9999-000000000000",
      "session_id": "c711a88b-2121-4999-88ab-7733221100aa",
      "role": "assistant",
      "content": "According to the architecture specifications [^1], the high availability target is 99.99%.",
      "citations": [
        {
          "index": 1,
          "document_id": "f512c12a-89a1-4389-9a21-998811aa22bb",
          "document_name": "architecture.pdf",
          "chunk_id": "b1111111-2222-3333-4444-555555555555",
          "content_excerpt": "Our target SLA is 99.99%...",
          "page_numbers": [4],
          "confidence": 0.94
        }
      ],
      "confidence_score": 0.94,
      "token_count": 28,
      "cost_usd": 0.0002,
      "feedback": "up",
      "feedback_note": "Accurate response with valid citation",
      "created_at": "2026-08-08T15:00:05Z"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

---

#### `POST /api/v1/chat/messages/{message_id}/feedback`
Records user thumbs-up / thumbs-down rating and optional feedback notes for an assistant message.

* **Auth required:** Yes
* **Path Parameters:** `message_id` (`UUID`)
* **Request Body:**
```json
{
  "feedback": "up", // Options: "up" | "down"
  "feedback_note": "Extremely accurate context quote." // Optional, max 2000 chars
}
```
* **Response (200 OK):** `ChatMessageResponse`

---

## 6. Comprehensive TypeScript Definitions Summary

```typescript
// Authentication Types
export type UserRole = 'owner' | 'admin' | 'member' | 'viewer';
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'revoked';

export interface UserResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface InvitationResponse {
  id: string;
  email: string;
  role: UserRole;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
}

export interface InvitationCreateResponse {
  invitation: InvitationResponse;
  invite_token: string;
}

// Workspace Types
export interface WorkspaceResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  dlp_rules: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

// Document Types
export type DocumentStatus = 'pending' | 'processing' | 'active' | 'error';

export interface DocumentResponse {
  id: string;
  workspace_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  content_hash: string;
  version: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentResponse;
  message: string;
}

// Chat & RAG Types
export interface CitationDetail {
  index: number;
  document_id: string;
  document_name: string;
  chunk_id: string;
  content_excerpt: string;
  page_numbers: number[];
  confidence: number;
}

export interface ChatSessionResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string | null;
  running_summary: string | null;
  message_count: number;
  total_tokens: number;
  total_cost_usd: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: CitationDetail[] | null;
  confidence_score: number | null;
  token_count: number;
  cost_usd: number;
  feedback: 'up' | 'down' | null;
  feedback_note: string | null;
  created_at: string;
}
```
