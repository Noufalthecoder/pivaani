'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

// onMessage is called synchronously for every frame. Prefer it over lastMessage:
// bursts (e.g. CASE_OPENED + two SPEAKs) can collapse into one React render,
// and lastMessage would then only expose the final event.
export function useWebSocket(url = 'ws://localhost:8000/ws', { onMessage } = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const socketRef = useRef(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage
  // event_ids already handled; shared across reconnects so a frame is never processed twice
  const seenEventIdsRef = useRef(new Set())

  useEffect(() => {
    if (typeof window === 'undefined') return

    // Each effect run owns exactly one live socket. Once disposed (unmount,
    // StrictMode double-mount, hot reload) it must neither deliver messages nor
    // reconnect; a leaked socket would make every SPEAK play once per socket.
    let disposed = false
    let ws = null
    let reconnectTimer = null

    const connect = () => {
      if (disposed) return
      try {
        ws = new WebSocket(url)
        socketRef.current = ws
      } catch (err) {
        console.warn('[WebSocket] Failed to initialize WebSocket:', err)
        reconnectTimer = setTimeout(connect, 3000)
        return
      }

      ws.onopen = () => {
        if (disposed) return
        setIsConnected(true)
        console.log('[WebSocket] Connected to Pi Vaani backend:', url)
      }

      ws.onmessage = (event) => {
        if (disposed) return
        try {
          const parsed = JSON.parse(event.data)
          if (parsed.event_id) {
            const seen = seenEventIdsRef.current
            if (seen.has(parsed.event_id)) return
            seen.add(parsed.event_id)
            if (seen.size > 500) seen.delete(seen.values().next().value)
          }
          setLastMessage(parsed)
          if (onMessageRef.current) onMessageRef.current(parsed)
        } catch (e) {
          // In case of non-JSON ping/pong strings
          setLastMessage({ type: 'RAW', payload: event.data })
        }
      }

      ws.onclose = () => {
        if (disposed) return
        setIsConnected(false)
        console.log('[WebSocket] Disconnected. Reconnecting in 2s...')
        reconnectTimer = setTimeout(connect, 2000)
      }

      ws.onerror = () => {
        ws.close() // onclose schedules the reconnect
      }
    }

    connect()

    return () => {
      disposed = true
      clearTimeout(reconnectTimer)
      if (ws) ws.close()
      socketRef.current = null
    }
  }, [url])

  const sendMessage = useCallback((msg) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
  }, [])

  return { isConnected, lastMessage, sendMessage }
}
