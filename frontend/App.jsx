'use client'

import React, { useState, useEffect } from 'react'
import Demo from './Demo'

/**
 * App component supporting route resolution for /demo
 */
export default function App() {
  const [currentPath, setCurrentPath] = useState('/demo')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setCurrentPath(window.location.pathname || '/demo')

      const handlePopState = () => {
        setCurrentPath(window.location.pathname || '/demo')
      }
      window.addEventListener('popstate', handlePopState)
      return () => window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  // Route /demo to Demo component
  if (currentPath === '/demo' || currentPath === '/' || currentPath.startsWith('/demo')) {
    return <Demo />
  }

  return <Demo />
}

