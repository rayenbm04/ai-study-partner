# RAG Assistant — Frontend

React + Vite client for the [RAG Multimodal Assistant](../README.md). Provides the chat interface, document management, auth, and usage dashboard for the FastAPI backend.

See the [root README](../README.md) for the full project architecture, retrieval pipeline, and benchmarks. This document covers the frontend specifically.

---

## Features

- **Three-column layout** — sessions list (left), streaming chat (centre), documents panel (right)
- **Streaming chat** with markdown rendering (`react-markdown` + `remark-gfm` + `remark-math`/`rehype-katex` for math, `rehype-highlight` for code blocks)
- **Auth** — login/register views backed by the FastAPI JWT endpoints; session persisted in `localStorage`
- **Document upload & management** — drag-and-drop upload zone, per-file cards with status, re-index and delete actions
- **Document preview** — PDF via native iframe viewer, PPTX/DOCX/XLSX via backend-side LibreOffice conversion, images and plain text rendered directly
- **Cancel & restore** — cancel an in-flight answer and get the question back in the input bar to edit and resend
- **Usage dashboard** (`recharts`) — questions asked, response times, chunk counts, token usage, active models
- **Prompt navigator** — jump to any previous question in the current session
- **PDF export** of the current chat via the browser print dialog

---

## Tech stack

| Layer | Library |
|---|---|
| Build tool | Vite 6 |
| UI framework | React 19 |
| Styling | Tailwind CSS 4, `tw-animate-css` |
| Components | Radix UI primitives (`radix-ui`), `shadcn`-style wrappers in `src/components/ui/` |
| Animation | Framer Motion / `motion` |
| Icons | Lucide React, Remix Icon |
| Markdown/math | `react-markdown`, `remark-gfm`, `remark-math`, `rehype-katex`, `rehype-highlight`, `react-syntax-highlighter` |
| Charts | Recharts |
| Testing | Vitest, Testing Library, jsdom |

---

## Project structure

```
rag-frontend/
├── src/
│   ├── App.jsx              # Main app — auth, sessions, chat, upload, dashboard (single-file SPA logic)
│   ├── App.css / index.css  # Global styles
│   ├── main.jsx              # Entry point
│   ├── test/setup.js         # Vitest setup (jest-dom matchers)
│   ├── components/
│   │   ├── AnswerDisplay.jsx  # Renders streamed answers, citations, F/R eval badges
│   │   ├── Composer.jsx       # Chat input bar (send/cancel)
│   │   ├── FileCard.jsx       # Document panel file row (status, reindex, delete)
│   │   ├── UploadZone.jsx     # Drag-and-drop upload
│   │   ├── SessionItem.jsx    # Sessions list entry
│   │   ├── Markdown.jsx       # Markdown renderer wrapper
│   │   ├── TypingIndicator.jsx
│   │   ├── Background.jsx
│   │   └── ui/                # Radix/shadcn-style primitives (button, dialog, card, sheet, tooltip, etc.)
│   └── lib/utils.js
├── vite.config.js
├── nginx.conf                 # Used by the Docker build to serve the production bundle
└── Dockerfile
```

---

## Setup

### Prerequisites

- Node.js 18+
- The FastAPI backend running (see [rag-backend](../rag-backend)) — required for auth, chat, and document features

### Install & run

```bash
npm install
cp .env.local.example .env.local   # edit VITE_API_URL if the backend isn't on localhost:8000
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

Copy `.env.local.example` to `.env.local` — Vite loads `.env.local` automatically and it's gitignored (`*.local`).

### Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
| `npm test` | Run the Vitest test suite |

---

## Testing

Component tests live alongside their source files (`*.test.jsx` / `*.test.js`) and use Vitest + React Testing Library, running in a jsdom environment. Run them with:

```bash
npm test
```

CI runs this same command on every push/PR via `.github/workflows/tests.yml`.

---

## Docker

The frontend has its own `Dockerfile` and is built/served as part of the root `docker-compose.yml`:

```bash
cd ..
docker compose up --build
```

This builds the production bundle and serves it via nginx (`nginx.conf`) at [http://localhost](http://localhost), proxying API calls to the backend container.
