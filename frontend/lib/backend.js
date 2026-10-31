// Backend address. Set NEXT_PUBLIC_BACKEND_URL (e.g. https://pivaani-api.onrender.com)
// when the FastAPI backend is hosted; locally it defaults to http://localhost:8000.
export const BACKEND_HTTP = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '')

// Same host over WebSockets: http -> ws, https -> wss
export const BACKEND_WS = `${BACKEND_HTTP.replace(/^http/, 'ws')}/ws`
