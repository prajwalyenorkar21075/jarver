# JARVIS

Voice-controlled 3D assistant UI.

## Stack

- **Frontend** — Vite + React + TypeScript, Three.js (`@react-three/fiber`), GSAP, Zustand, Tailwind v4
- **Backend** — Python / FastAPI / Uvicorn (Pocket TTS + LLM proxy + tool-calling agent)

## Layout

```
jarvis/
├── frontend/     React + Three.js + GSAP UI
├── backend/      FastAPI: TTS, STT, LLM proxy, agent tools
└── Agent Memory/ (sibling) session notes and learnings
```

## Run

```bash
# backend  (NOTE: use the venv python directly, see Agent Memory learnings/env-gotchas.md)
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm run dev
```

Open http://localhost:5173

## Steps

- [x] 1. Scaffold + 3D particle field + FastAPI health endpoint
- [x] 2. GSAP panel choreography (zoom in -> dock top-right) + Full UI
- [x] 3. LLM interface (Groq openai/gpt-oss-120b wired into /api/chat)
- [ ] 4. Pocket TTS streaming voice output
- [ ] 5. Speech-to-text + wake word (Web Speech API wired)
- [ ] 6. In-app browser/search panel (In-app verified search ready)
