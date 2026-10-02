# JARVIS Frontend Redesign: Live Coding Workspace — SPEC.md

**Phase:** 001  
**Type:** Major Frontend Architecture Overhaul  
**Date:** 2026-09-30  
**Status:** SPEC — Awaiting Discussion

---

## 1. EXECUTIVE SUMMARY

Transform the Jarvis frontend from a dashboard-centric UI into a **production-grade Live Coding Workspace** comparable to ChatGPT/Cursor, with:

- **Streaming token-by-token responses** — never block the UI; show output as it arrives
- **Dual-panel layout** — Conversation (left) + Live Agent Workspace (right)
- **Real-time agent observability** — File edits, diffs, terminal, errors in dedicated side panel
- **Fixed built-in browser** — Full navigation, refresh, error display, correct frontend preview
- **Drag-and-drop file/image upload** — Attachments visible in chat, AI can inspect/use them
- **Zero mock/demo code** — Every feature wired to real backend endpoints

---

## 2. CURRENT STATE ANALYSIS

### What Works
- Backend: FastAPI + WebSocket (`/api/coding/ws/{session_id}`) + REST endpoints for coding tools
- Backend tools: `workspace_tree`, `read_file`, `write_file`, `patch_file`, `grep_search`, `rollback_file`, `run_command`, `git_status`, `upload_file`, `list_uploads`
- Frontend: `JarvisCodingWorkbench.tsx` has substantial UI but **not streaming**, **not split conversation/workspace**, browser panel uses static snapshots
- Socket service exists but only sends final results, not streaming tokens

### Critical Gaps
| Area | Current | Required |
|------|---------|----------|
| **Streaming** | Single bulk response after 30-120s | Token-by-token SSE/WebSocket streaming |
| **Layout** | Single full-screen workbench | Split: Conversation (60%) + Agent Workspace (40%) |
| **Browser** | Static Chromium snapshots via `/api/browser/preview` | Live iframe + navigation + error handling |
| **File Upload** | Button-only, no drag-drop, no chat integration | Drag-drop + button + attachment pills in chat |
| **Agent Visibility** | Only final diffs in chat | Live side panel: file tree, diffs, terminal, errors as they happen |

---

## 3. FUNCTIONAL REQUIREMENTS (FALSIFIABLE)

### FR-1: Streaming Chat Architecture
- **FR-1.1** Replace `/api/chat` polling with **Server-Sent Events (SSE)** endpoint `/api/chat/stream` that yields tokens as `data: { "delta": "token" }\n\n`
- **FR-1.2** Frontend `useJarvisStore` accumulates deltas into message buffer; UI re-renders on each chunk (not batched)
- **FR-1.3** Orb state transitions: `idle` → `thinking` (first token) → `solving` (complete) — no 1-2 minute freeze
- **FR-1.4** Backward compatibility: `/api/chat` remains for non-streaming fallback

### FR-2: Dual-Panel Live Coding Workspace
- **FR-2.1** New route `/workspace` (or toggle in main UI) renders `LiveWorkspace` component
- **FR-2.2 Left Panel (Conversation)**: 
  - Streaming message bubbles with sender, timestamp, copy button
  - Attachment pills below user messages (images preview, files with icons)
  - Input area: text + drag-drop zone + upload button + send
- **FR-2.3 Right Panel (Agent Workspace)** — 4 tabs:
  1. **Files** — Live tree with active file highlight, diff preview on hover
  2. **Diffs** — Unified diff viewer with accept/reject per hunk (future)
  3. **Terminal** — Live command output with ANSI color, scroll lock toggle
  4. **Errors** — Aggregated error list with file:line links
- **FR-2.4** Responsive: stacks on mobile, side-by-side on desktop (≥1024px)

### FR-3: Fixed Built-in Browser/Preview
- **FR-3.1** Replace static `/api/browser/preview` image with **live iframe sandbox** (`sandbox="allow-scripts allow-same-origin allow-forms allow-popups"`)
- **FR-3.2** Navigation bar: back, forward, refresh, URL input, "Open in New Tab"
- **FR-3.3** Error boundary: show friendly error UI when iframe fails to load (CSP, network, 404)
- **FR-3.4** Works for `http://localhost:5173` (self-preview), external sites, and `file://` via backend proxy if needed
- **FR-3.5** Keep existing Google/YouTube/Dossier tabs as secondary features

### FR-4: Chat File/Image Upload
- **FR-4.1** Drag-and-drop zone in chat input area (visual feedback on drag-enter)
- **FR-4.2** "Attach File" button opens native file picker
- **FR-4.3** Upload via existing `/api/upload` (base64) — show progress, then render attachment pill
- **FR-4.4** Attachment pill shows: icon (by mime-type), filename, size, ✕ remove
- **FR-4.5** Images render as inline preview (max 300px) in chat bubble
- **FR-4.6** Backend: AI receives attachment list in context; can call `read_file` on uploaded paths

### FR-5: Agent Workspace Real-Time Updates
- **FR-5.1** WebSocket `/api/coding/ws/{session_id}` broadcasts **incremental events**:
  - `tool_start` — `{ tool, args }`
  - `tool_result` — `{ tool, result, diff? }`
  - `terminal_output` — `{ cmd, stdout, stderr, exit_code }`
  - `error` — `{ file, line, message, severity }`
- **FR-5.2** Frontend subscribes and updates right-panel tabs in real-time
- **FR-5.3** Terminal tab: ANSI-to-HTML rendering, auto-scroll with lock toggle

### FR-6: State Management & Performance
- **FR-6.1** Virtualized message list (react-window) for 1000+ messages
- **FR-6.2** Memoized diff rendering (only changed hunks re-render)
- **FR-6.3** WebSocket reconnection with exponential backoff
- **FR-6.4** No blocking renders during streaming — use `requestAnimationFrame` batching

---

## 4. NON-FUNCTIONAL REQUIREMENTS

| NFR | Target |
|-----|--------|
| **First token latency** | < 500ms from user Enter |
| **UI responsiveness during streaming** | 60fps, no jank |
| **Bundle size increase** | < 150KB gzipped |
| **Memory growth per 100 messages** | < 10MB |
| **WebSocket reconnect time** | < 2s after network blip |
| **Accessibility** | WCAG 2.1 AA for chat/workspace |

---

## 5. ACCEPTANCE CRITERIA (VERIFIABLE)

| ID | Scenario | Pass Condition |
|----|----------|----------------|
| AC-1 | User types "create a React counter component" | First token appears <500ms; full response streams token-by-token; orb shows `thinking` |
| AC-2 | Agent writes `Counter.tsx` via `write_file` | Right panel Files tab shows new file; Diffs tab shows unified diff; Terminal shows no errors |
| AC-3 | User drags `screenshot.png` into chat | Attachment pill appears; image preview renders; backend receives upload; AI can reference it |
| AC-4 | User navigates to `http://localhost:5173` in browser tab | Live iframe loads frontend; refresh button works; console errors surface in Errors tab |
| AC-5 | Agent runs `npm run build` via `run_command` | Terminal tab streams stdout/stderr line-by-line; exit code shown |
| AC-6 | Network disconnects during streaming | WebSocket reconnects; message history preserved; streaming resumes or fails gracefully |
| AC-7 | Mobile viewport (375px) | Panels stack; conversation scrollable; workspace tabs swipeable |

---

## 6. TECHNICAL ARCHITECTURE DECISIONS (LOCKED)

| Decision | Rationale |
|----------|-----------|
| **SSE for streaming** | Simpler than WebSocket for unidirectional server→client; works over HTTP/2; auto-reconnect |
| **Keep WebSocket for agent events** | Bidirectional; low latency for tool/terminal/error events |
| **React 19 + concurrent features** | `useTransition`, `useDeferredValue` for non-blocking streaming renders |
| **Zustand store split** | Separate `useConversationStore` + `useAgentWorkspaceStore` to avoid re-render storms |
| **No new backend framework** | Existing FastAPI + WebSocket + tools sufficient; only add SSE endpoint |
| **shadcn/ui + Tailwind v4** | Existing stack; consistent with current aesthetic |

---

## 7. OUT OF SCOPE (EXPLICIT)

- Multi-user collaboration
- Git diff UI (accept/reject hunks) — backend supports, UI deferred
- Voice input in workspace (keep existing voice bar)
- Code execution sandbox (backend `run_command` is sufficient)
- Mobile app / PWA

---

## 8. DEPENDENCIES

### New Frontend Dependencies
```json
{
  "react-window": "^1.8.10",
  "ansi-to-html": "^0.7.2",
  "lucide-react": "^0.460.0",
  "clsx": "^2.1.1",
  "tailwind-merge": "^2.5.4"
}
```

### Backend Changes
- Add `/api/chat/stream` SSE endpoint (reuses existing LLM logic)
- Enhance WebSocket to emit incremental tool/terminal/error events
- Ensure `/api/upload` returns accessible file paths for AI context

---

## 9. MIGRATION STRATEGY

1. **Phase 1** (this SPEC): Build new `LiveWorkspace` alongside existing `JarvisCodingWorkbench` — feature flag via store
2. **Phase 2**: Migrate chat to SSE streaming; add attachment UI
3. **Phase 3**: Replace browser panel with live iframe; integrate into workspace
4. **Phase 4**: Deprecate `JarvisCodingWorkbench`; make `LiveWorkspace` default
5. **Phase 5**: Polish, accessibility, performance profiling

---

## 10. RISKS & MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SSE proxy buffering (nginx/Vite) | Medium | High | Configure `proxy_request_buffering off` in Vite proxy; test early |
| WebSocket message ordering | Low | Medium | Sequence numbers on events; client-side reorder buffer |
| Large file uploads blocking UI | Medium | Medium | Chunked upload via `FileReader` + progress; Web Worker for base64 |
| Memory leak in streaming buffer | Low | High | Cap message history at 200; virtualize list; WeakMap for diffs |

---

## 11. SUCCESS METRICS

- **Time to first token** < 500ms (p95)
- **Zero UI freezes** during 5-minute coding session
- **All 7 ACs pass** in manual E2E test
- **Bundle size** < 1.2MB (current ~1.05MB)
- **Zero console errors** in browser devtools during typical session

---

## 12. APPROVAL

This SPEC is ready for discussion. Once approved, `/gsd-discuss-phase 001` will extract implementation decisions into `001-CONTEXT.md`.