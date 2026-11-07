# Tech Skill Tracker — Frontend

React + TypeScript + Vite + Tailwind CSS (shadcn/ui base-nova) frontend for the FastAPI backend.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

The frontend expects the FastAPI backend at `VITE_API_BASE` (default `http://localhost:8000`).

```bash
# in the repo root, separate terminal:
uvicorn backend.main:app --reload --port 8000
```

## Build / Test

```bash
npm run build      # tsc -b && vite build
npm run test       # vitest run
npm run lint       # oxlint
```

## Path aliases

`@/…` maps to `src/…` (see `vite.config.ts` and `tsconfig.app.json`). `components.json` declares the shadcn aliases and Nova theme; `src/index.css` holds the Nova CSS variables.
