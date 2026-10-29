'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(url = 'ws://localhost:8000/ws') {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const socketRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return

    try {
      const ws = new WebSocket(url)
      socketRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        console.log('[WebSocket] Connected to Pi Vaani backend:', url)
      }

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          setLastMessage(parsed)
        } catch (e) {
          // In case of non-JSON ping/pong strings
          setLastMessage({ type: 'RAW', payload: event.data })
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log('[WebSocket] Disconnected. Reconnecting in 2s...')
        reconnectTimeoutRef.current = setTimeout(connect, 2000)
      }

      ws.onerror = (err) => {
        console.warn('[WebSocket] Connection error:', err)
        ws.close()
      }
    } catch (err) {
      console.warn('[WebSocket] Failed to initialize WebSocket:', err)
      reconnectTimeoutRef.current = setTimeout(connect, 3000)
    }
  }, [url])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [connect])

  const sendMessage = useCallback((msg) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
  }, [])

  return { isConnected, lastMessage, sendMessage }
}

