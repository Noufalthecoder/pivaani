# Pi Vaani — Bharosa Layer for UPI

> Deterministic UPI payment safety layer with a 7-gate trust firewall, real-time WebSocket events, audit hash chain, distributed idempotency locks, and graph-based fraud detection.

## Project Structure

```
pivaani/
├── frontend/          # Next.js 16 app (React + Tailwind)
│   ├── app/           # App Router pages
│   │   ├── page.tsx   # Landing page (/)
│   │   └── demo/      # Demo dashboard (/demo)
│   ├── components/    # Shared UI components
│   ├── lib/           # Hooks and utilities
│   ├── public/        # Static assets
│   ├── Demo.jsx       # Full demo dashboard component
│   ├── App.jsx        # Client-side router
│   └── package.json
│
└── backend/           # FastAPI backend
    ├── main.py        # App entrypoint, REST + WebSocket
    ├── models.py      # SQLAlchemy ORM models
    ├── audit.py       # SHA-256 hash chain audit log
    ├── events.py      # WebSocket connection manager
    ├── cases.py       # Case State Machine (background task)
    ├── firewall.py    # 7-gate trust evaluation engine
    ├── locks.py       # Async distributed idempotency locks
    ├── fraud_graph.py # NetworkX fraud ring detector
    ├── sandbox.py     # Mock payment helpers
    ├── routers/
    │   └── sandbox_api.py  # Sandbox REST endpoints
    └── requirements.txt
```

## Quick Start

### Backend (FastAPI)
```bash
cd pivaani
python -m uvicorn main:app --app-dir ./backend --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)
```bash
cd pivaani/frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000/demo](http://localhost:3000/demo)

## Architecture

- **7-Gate Firewall**: Authority → Amount → Confidence → Identity → Idempotency → Reversibility → Approval
- **Audit Hash Chain**: Each event hashes the previous event — tamper-evident log
- **Distributed Lock**: `asyncio.Lock()` per idempotency key — blocks double-spends at 10ms resolution
- **Fraud Graph**: NetworkX detects collusive retap patterns across merchant-customer edges
- **Case State Machine**: Background task opens `PV-xxxx` cases for stuck payments within 2 seconds

## Team
ImpactMinds — Pi Vaani
