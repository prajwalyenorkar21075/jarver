# JARVIS Frontend Redesign: Live Coding Workspace — PLAN.md

**Phase:** 001  
**SPEC:** `.planning/phase-001-SPEC.md`  
**Status:** PLAN — Ready for Execution  
**Mode:** Tracer-first (vertical slice)

---

## EXECUTION STRATEGY

**Tracer Slice (Task 1):** End-to-end streaming chat with minimal UI — proves SSE + WebSocket + store integration works before building full workspace.

**Expansion Tasks (2-8):** Each adds one workspace panel feature, verified independently.

---

## TASK BREAKDOWN

### Task 1: Streaming Chat Infrastructure (TRACER)
**Goal:** Replace `/api/chat` polling with SSE streaming; messages appear token-by-token.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 1.1 | Add `/api/chat/stream` SSE endpoint in `backend/app/main.py` | `curl -N /api/chat/stream` yields `data: {"delta":"..."} ` |
| 1.2 | Create `useConversationStore.ts` (split from `useJarvisStore`) | Store has `messages`, `streamingMessageId`, `appendDelta(id, delta)` |
| 1.3 | Build `StreamingChatPanel.tsx` — minimal conversation UI | Type "hello" → tokens stream in real-time, orb shows `thinking` |
| 1.4 | Wire SSE client in `StreamingChatPanel` with reconnection | Network disconnect → reconnects, history preserved |
| 1.5 | Add `stream: true` flag to `executeCommand` in store | Existing voice/text commands use streaming automatically |

**Acceptance:** AC-1 passes (first token <500ms, streaming visible, no UI freeze)

---

### Task 2: Dual-Panel Layout & Conversation Polish
**Goal:** Split view with conversation left, workspace right; polished message bubbles.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 2.1 | Create `LiveWorkspace.tsx` with CSS Grid layout (60/40 split, responsive) | Desktop: side-by-side; Mobile: stacked |
| 2.2 | Move `StreamingChatPanel` into left panel | Conversation renders in left 60% |
| 2.3 | Add message bubbles: sender badge, timestamp, copy button, markdown rendering | Visual match to ChatGPT/Cursor |
| 2.4 | Virtualize message list with `react-window` (cap 200 messages) | 1000 messages → 60fps scroll |
| 2.5 | Add attachment pill UI (placeholder, no upload yet) | Pill renders below user message |

**Acceptance:** Layout renders correctly at 1440px, 1024px, 375px

---

### Task 3: File/Image Upload in Chat
**Goal:** Drag-drop + button upload → attachment pills → backend `/api/upload` → AI context.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 3.1 | Add drop zone + file input to chat input area | Drag file → zone highlights; click → picker opens |
| 3.2 | Implement upload to `/api/upload` with progress + base64 | File appears in `uploads/` dir; response has `path` |
| 3.3 | Render attachment pills: icon by mime-type, filename, size, ✕ remove | Image shows preview; code file shows icon |
| 3.4 | Include attachment paths in SSE request context | Backend receives `attachments: [{path, mime_type}]` |
| 3.5 | Backend: AI can call `read_file` on uploaded paths | Agent reads uploaded file content in reasoning |

**Acceptance:** AC-3 passes (drag image → preview renders; upload succeeds; AI can reference)

---

### Task 4: Agent Workspace — Files Tab (Live Tree + Diffs)
**Goal:** Right panel Files tab shows workspace tree with live updates; diff preview on tool calls.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 4.1 | Create `AgentWorkspace.tsx` with 4 tabs (Files, Diffs, Terminal, Errors) | Tabs switch; state preserved |
| 4.2 | Files tab: virtualized tree from `/api/coding/workspace/tree` | Expand/collapse works; file click highlights |
| 4.3 | Subscribe to WebSocket `tool_result` events with `diff` field | Diff appears in Files tab sidebar on `write_file`/`patch_file` |
| 4.4 | Diff viewer: unified diff with syntax highlighting (prismjs or light) | Added/removed lines colored; file:line links |
| 4.5 | Active file tracking: highlight file being edited in tree | Tree updates in real-time during agent work |

**Acceptance:** AC-2 passes (agent writes file → tree updates → diff visible)

---

### Task 5: Agent Workspace — Terminal Tab (Live Output)
**Goal:** Real-time terminal output with ANSI colors, scroll lock.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 5.1 | Terminal tab: WebSocket `terminal_output` event subscription | Command output streams line-by-line |
| 5.2 | ANSI-to-HTML rendering via `ansi-to-html` | Colors render correctly (green/red/cyan) |
| 5.3 | Auto-scroll with lock toggle (↻ button) | Scroll lock pauses auto-scroll |
| 5.4 | Command prompt styling: `JARVIS-SHELL > cmd` | Matches existing terminal aesthetic |

**Acceptance:** AC-5 passes (`npm run build` streams stdout/stderr with colors)

---

### Task 6: Agent Workspace — Errors Tab + Diffs Tab
**Goal:** Aggregated error list + dedicated diff viewer.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 6.1 | Errors tab: WebSocket `error` event subscription | Errors appear with file:line:col |
| 6.2 | Error items link to Files tab (scroll to file) | Click error → Files tab opens file |
| 6.3 | Diffs tab: collects all diffs from session, grouped by file | Unified diff list with file headers |
| 6.4 | Diff hunk expand/collapse | Large diffs manageable |

**Acceptance:** Agent syntax error → appears in Errors tab with link

---

### Task 7: Fixed Built-in Browser (Live Iframe)
**Goal:** Replace static snapshot browser with live iframe + navigation + error handling.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 7.1 | Create `LiveBrowserPanel.tsx` with iframe + nav bar (back, forward, refresh, URL) | Navigate to google.com → loads |
| 7.2 | Sandbox iframe: `allow-scripts allow-same-origin allow-forms allow-popups` | External sites load; CSP respected |
| 7.3 | Error boundary: catch iframe load errors → friendly UI | 404/CSP/network error → "Failed to load" with retry |
| 7.4 | Self-preview: `http://localhost:5173` loads correctly | Frontend renders in iframe |
| 7.5 | Integrate as tab in Agent Workspace (or keep as separate panel) | Browser accessible from workspace |

**Acceptance:** AC-4 passes (navigate, refresh, error display all work)

---

### Task 8: Integration, Polish & Migration
**Goal:** Wire everything together; deprecate old workbench; performance pass.

| Subtask | Description | Verification |
|---------|-------------|--------------|
| 8.1 | Add workspace toggle to main UI (BottomBar or TopNavBar) | "Code Mode" button opens LiveWorkspace |
| 8.2 | Migrate `executeCommand` to use new streaming + workspace | Voice "code mode" → opens workspace with streaming |
| 8.3 | Performance: memoize diff/terminal components; profile bundle | Bundle < 1.2MB; no memory leaks in 10-min session |
| 8.4 | Accessibility: ARIA labels, keyboard nav, focus management | WCAG 2.1 AA spot-check |
| 8.5 | E2E test all 7 ACs manually | All ACs pass; no console errors |

**Acceptance:** All ACs pass; ready for production

---

## DEPENDENCY GRAPH

```
Task 1 (TRACER) ──▶ Task 2 ──▶ Task 3
                        │
                        ├─▶ Task 4 ──▶ Task 6
                        │
                        ├─▶ Task 5
                        │
                        └─▶ Task 7
                              │
                              ▼
                        Task 8 (Integration)
```

---

## VERIFICATION CHECKLIST

| Check | Command/Method |
|-------|----------------|
| TypeScript compiles | `npm run build` in frontend |
| Backend starts | `cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` |
| SSE endpoint works | `curl -N http://localhost:8000/api/chat/stream -d '{"messages":[{"role":"user","content":"hi"}]}'` |
| WebSocket connects | Browser devtools Network tab → WS frames visible |
| Frontend dev server | `cd frontend && npm run dev` → http://localhost:5173 |
| All 7 ACs pass | Manual test script (see below) |

---

## MANUAL E2E TEST SCRIPT (for Task 8)

```bash
# 1. Start backend + frontend
# 2. Open http://localhost:5173
# 3. Click "Code Mode" → LiveWorkspace opens
# 4. Type: "Create a React counter component with useState"
#    → Verify: tokens stream immediately (AC-1)
#    → Verify: Files tab shows new Counter.tsx (AC-2)
#    → Verify: Diffs tab shows unified diff (AC-2)
# 5. Drag screenshot.png into chat
#    → Verify: attachment pill with preview (AC-3)
# 6. Type: "Run npm run build"
#    → Verify: Terminal tab streams colored output (AC-5)
# 7. Click Browser tab → navigate to http://localhost:5173
#    → Verify: iframe loads, refresh works (AC-4)
# 8. Introduce syntax error in agent prompt
#    → Verify: Errors tab shows error with file:line (AC-6)
# 9. Resize to 375px width
#    → Verify: panels stack, tabs swipeable (AC-7)
```

---

## ROLLBACK PLAN

If any task breaks existing functionality:
1. `git stash` changes
2. `start_jarvis.ps1` still works with old `JarvisCodingWorkbench`
3. Fix forward or revert task

---

## ESTIMATED EFFORT

| Task | Est. Hours | Risk |
|------|------------|------|
| 1 (Tracer) | 3 | Medium (SSE proxy config) |
| 2 | 2 | Low |
| 3 | 3 | Medium (base64 large files) |
| 4 | 3 | Medium (WS event ordering) |
| 5 | 2 | Low |
| 6 | 1 | Low |
| 7 | 2 | Medium (iframe sandbox CSP) |
| 8 | 2 | Low |
| **Total** | **~18** | |

---

## NEXT STEPS

1. Execute Task 1 (Tracer) — verify streaming works end-to-end
2. Present Task 1 results for verification
3. Proceed to Task 2-3 in parallel (layout + upload)
4. Tasks 4-6 in parallel (workspace panels)
5. Task 7 (browser)
6. Task 8 (integration)

**Ready to execute Task 1.**