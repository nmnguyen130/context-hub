# ContextHub Frontend Foundation

This is the Next.js 16.3.0 frontend application for **ContextHub** - an Enterprise AI Knowledge Platform.

Built with **Next.js 16.3.0 (App Router)**, **React 19**, **TypeScript**, **Tailwind CSS (v4)**, **TanStack Query**, and **Zustand**.

---

## 1. Tech Stack Overview

- **Framework:** Next.js 16.3.0 (App Router, Turbopack)
- **UI & Styling:** Tailwind CSS v4, Radix UI primitives, Lucide React icons, Sonner toasts
- **State Management:** Sliced Zustand Stores (`ui-store`, `workspace-store`, `chat-store`, `tenant-store`)
- **Data Fetching:** TanStack Query (`@tanstack/react-query`) with automatic status polling
- **Authentication:** Edge Route Middleware (`proxy.ts`), HTTPOnly Secure Cookies, Zod validation
- **Streaming:** Custom SSE client (`stream-client.ts`) with native `AbortController` cancellation

---

## 2. Directory Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── (public)/         # Public Landing Page (Hero, Features, Pricing)
│   │   ├── auth/             # Login (/auth/login) & Register (/auth/register)
│   │   ├── app/              # Protected App Shell (Dashboard, Workspaces, Chat, Settings)
│   │   ├── globals.css       # Deep Nebula dark theme tokens & utility styles
│   │   └── layout.tsx        # Root layout with Outfit + Inter fonts and script handler
│   ├── components/
│   │   ├── ui/               # Reusable UI primitives (Button, Input, Card, Badge, Skeleton)
│   │   └── landing/          # Landing page sections (Navbar, Hero, Demo, Features, Pricing)
│   ├── features/             # Domain feature hooks and forms (Auth, Workspaces, Chat)
│   ├── lib/
│   │   ├── api/              # Modular API client wrappers (Client, Auth, Workspace, Chat)
│   │   └── chat/             # Cancelable SSE stream client and parser
│   ├── proxy.ts              # Next.js 16.3.0 Edge proxy route protection middleware
│   ├── store/                # Domain-specific Zustand stores
│   └── types/                # TypeScript interface models
├── Dockerfile                # Multi-stage production container build
├── .dockerignore             # Excludes node_modules and build cache from Docker context
├── next.config.ts            # Next.js standalone output configuration
└── package.json
```

---

## 3. Getting Started

### Local Development (Host Node)

```bash
# 1. Install dependencies
npm install

# 2. Start Next.js development server with Turbopack
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## 4. Key Application Features

1. **Multi-Tenant SSO Login & Tenant Registration**:
   - Organization slug lookup with HTTPOnly session cookies.
2. **Workspace & Document Management**:
   - Create workspaces, drag-and-drop file upload, real-time status polling.
3. **Grounded RAG Streaming Chat**:
   - SSE streaming response with inline citations (`[^[id]]`) showing page numbers, excerpts, and source document coordinates.
4. **Sliced Zustand Architecture**:
   - Decoupled domain state stores preventing unnecessary component re-renders.
