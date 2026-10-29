'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import {
  Mic,
  Shield,
  ShieldCheck,
  RotateCcw,
  Terminal,
  Send,
  X,
  Smartphone,
  Radio,
  Sliders,
  ChevronUp,
  Volume2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Sparkles
} from 'lucide-react'
import { useWebSocket } from '@/lib/useWebSocket'

const BACKEND_HTTP = 'http://localhost:8000'

export default function Demo() {
  // Navigation & Dial Mode
  const [dialMode, setDialMode] = useState('Balanced')
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [commandText, setCommandText] = useState('')
  const [isMicPressed, setIsMicPressed] = useState(false)

  // Payment & Case States
  // 'IDLE' | 'PROCESSING' | 'PENDING' | 'CONFIRMED'
  const [paymentStatus, setPaymentStatus] = useState('IDLE')
  const [currentPayment, setCurrentPayment] = useState(null)
  const [activeCase, setActiveCase] = useState(null)
  const [customerCaption, setCustomerCaption] = useState('Customer Captions will appear here')

  // Verification & Logs
  const [logs, setLogs] = useState([
    { time: '12:04:31', tag: 'system', text: 'Pi Vaani App loaded' },
    { time: '12:04:32', tag: 'firewall', text: 'Deterministic 7-Gate engine idle' }
  ])
  const [verifyResult, setVerifyResult] = useState(null)
  const [isVerifying, setIsVerifying] = useState(false)

  // Real-time WebSocket connection
  const { isConnected, lastMessage } = useWebSocket('ws://localhost:8000/ws')

  // Helper to add log entries
  const appendLog = useCallback((tag, text) => {
    const now = new Date()
    const timeStr = now.toTimeString().split(' ')[0]
    setLogs((prev) => [...prev.slice(-30), { time: timeStr, tag, text }])
  }, [])

  // 1. Initial State Fetch from FastAPI Backend
  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/api/state`)
      if (res.ok) {
        const data = await res.json()
        if (data.active_dial) {
          const capitalized = data.active_dial.charAt(0).toUpperCase() + data.active_dial.slice(1)
          setDialMode(capitalized)
        }
        if (data.active_cases && data.active_cases.length > 0) {
          setActiveCase(data.active_cases[0])
        } else {
          setActiveCase(null)
        }
        if (data.payments && data.payments.length > 0) {
          const latest = data.payments[0]
          setCurrentPayment(latest)
          if (latest.status === 'PENDING') {
            setPaymentStatus('PENDING')
          } else if (latest.status === 'SUCCESS') {
            setPaymentStatus('CONFIRMED')
          }
        }
      }
    } catch (err) {
      console.warn('Backend offline or starting up:', err.message)
    }
  }, [])

  useEffect(() => {
    fetchState()
  }, [fetchState])

  // 2. Real-time WebSocket Event Dispatcher
  useEffect(() => {
    if (!lastMessage) return

    const { type, payload } = lastMessage

    switch (type) {
      case 'HANDSHAKE':
        appendLog('system', 'Virtual Soundbox WebSocket connected')
        break

      case 'PAYMENT_CREATED':
        setCurrentPayment({
          id: payload.payment_id,
          amount: payload.amount,
          status: payload.status,
          rrn: payload.rrn
        })
        setPaymentStatus('PENDING')
        setCustomerCaption(`Payment ${payload.payment_id} initiated. Awaiting bank acknowledgement...`)
        appendLog('customer', `Payment initiated: ${payload.payment_id} (₹${payload.amount})`)
        break

      case 'CASE_OPENED':
        setActiveCase({
          id: payload.case_id,
          payment_id: payload.payment_id,
          status: payload.status,
          trigger_reason: payload.trigger_reason,
          amount: payload.amount
        })
        setCustomerCaption(`Payment stuck > 2s. Soundbox auto-opened Case ${payload.case_id}`)
        appendLog('firewall', `🚨 CASE_OPENED: ${payload.case_id} (${payload.trigger_reason})`)
        break

      case 'PAYMENT_UPDATED':
        if (payload.status === 'SUCCESS') {
          setPaymentStatus('CONFIRMED')
          setActiveCase(null) // Close case card
          setCustomerCaption(`Payment Confirmed! Ravi received ₹${payload.amount || 40}.`)
          appendLog('webhook', `Bank confirmed Payment ${payload.payment_id} -> Case Closed`)
        } else {
          appendLog('system', `Payment ${payload.payment_id} status updated to ${payload.status}`)
        }
        break

      case 'RETAP_DETECTED':
        setCustomerCaption('Retap detected! Idempotency Gate suppressed duplicate debit.')
        appendLog('firewall', 'Duplicate tap detected -> Idempotency Gate Active')
        break

      case 'STATE_RESET':
        setPaymentStatus('IDLE')
        setCurrentPayment(null)
        setActiveCase(null)
        setCustomerCaption('Customer Captions will appear here')
        appendLog('system', 'Sandbox reset to initial baseline')
        break

      case 'TRUST_DIAL_CHANGED':
        if (payload.trust_dial) {
          const cap = payload.trust_dial.charAt(0).toUpperCase() + payload.trust_dial.slice(1)
          setDialMode(cap)
          appendLog('merchant', `Trust dial switched to ${cap}`)
        }
        break

      default:
        break
    }
  }, [lastMessage, appendLog])

  // 3. Keyboard listener for 'C' to toggle Drawer
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault()
        setIsDrawerOpen((prev) => !prev)
      } else if (e.key === 'Escape') {
        setIsDrawerOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // 4. API Action: Customer clicks Pay button
  const handleCustomerPay = async () => {
    if (paymentStatus === 'PROCESSING') return

    setPaymentStatus('PROCESSING')
    setCustomerCaption('Contacting UPI payment gateway...')
    appendLog('customer', 'User tapped Pay ₹40')

    try {
      const res = await fetch(`${BACKEND_HTTP}/api/sandbox/pay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: 40, scenario: 'pending' })
      })
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`)
      }
      const data = await res.json()
      setCurrentPayment(data)
      setPaymentStatus('PENDING')
    } catch (err) {
      console.error('Pay error:', err)
      setPaymentStatus('IDLE')
      setCustomerCaption('Payment failed to initialize. Ensure backend is running.')
      appendLog('system', `Pay error: ${err.message}`)
    }
  }

  // 5. API Action: Force Payment to SUCCESS
  const handleForceSuccess = async () => {
    const paymentId = currentPayment?.id || currentPayment?.payment_id
    if (!paymentId) {
      appendLog('system', 'No payment active to force confirm. Creating new payment first...')
      await handleCustomerPay()
      return
    }

    try {
      const res = await fetch(`${BACKEND_HTTP}/api/sandbox/payments/${paymentId}/state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'SUCCESS' })
      })
      if (res.ok) {
        appendLog('scenario', `Forced payment ${paymentId} -> SUCCESS`)
      }
    } catch (err) {
      appendLog('system', `Failed to update payment: ${err.message}`)
    }
  }

  // 6. API Action: Retap
  const handleRetap = async () => {
    try {
      await fetch(`${BACKEND_HTTP}/api/sandbox/retap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_id: currentPayment?.id })
      })
    } catch (err) {
      appendLog('system', `Retap error: ${err.message}`)
    }
  }

  // 7. API Action: Reset Sandbox
  const handleResetSandbox = async () => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/api/reset`, { method: 'POST' })
      if (res.ok) {
        setPaymentStatus('IDLE')
        setCurrentPayment(null)
        setActiveCase(null)
        setCustomerCaption('Customer Captions will appear here')
        appendLog('system', 'Sandbox successfully reset')
      }
    } catch (err) {
      appendLog('system', `Reset error: ${err.message}`)
    }
  }

  // 8. API Action: Switch Trust Dial
  const handleDialChange = async (mode) => {
    setDialMode(mode)
    try {
      await fetch(`${BACKEND_HTTP}/api/merchant/dial`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trust_dial: mode.toLowerCase() })
      })
    } catch (err) {
      console.warn('Dial update offline:', err.message)
    }
  }

  // 9. API Action: Verify Audit Integrity
  const handleVerifyIntegrity = async () => {
    setIsVerifying(true)
    try {
      const res = await fetch(`${BACKEND_HTTP}/api/audit/verify`)
      const data = await res.json()
      setVerifyResult(data)
      appendLog(
        'audit',
        data.valid
          ? `✓ Hash chain verified: ${data.total_events} blocks intact`
          : `✗ Integrity broken at event ${data.broken_at_id}`
      )
    } catch (err) {
      setVerifyResult({ valid: false, message: 'Could not reach audit backend' })
    } finally {
      setIsVerifying(false)
      setTimeout(() => setVerifyResult(null), 5000)
    }
  }

  const gates = [
    { name: 'Authority', desc: 'Signer verification & channel origin' },
    { name: 'Amount', desc: 'Threshold check within merchant bounds' },
    { name: 'Confidence', desc: 'Acoustic & intent certainty threshold' },
    { name: 'Identity', desc: 'Voice biometric & payer alignment' },
    { name: 'Idempotency', desc: 'Duplicate suppression within 2s window' },
    { name: 'Reversibility', desc: 'Escrow buffer before settlement' },
    { name: 'Approval', desc: 'Merchant vocal confirmation if required' }
  ]

  return (
    <div
      className="min-h-screen text-[#FAFAFA] flex flex-col font-sans relative overflow-x-hidden selection:bg-[#FF5426]/30 selection:text-white"
      style={{ backgroundColor: '#0A0B0F' }}
    >
      {/* 1. TOP BAR (HEADER) */}
      <header
        className="h-16 px-6 flex items-center justify-between border-b shrink-0 z-30"
        style={{
          backgroundColor: '#14161C',
          borderColor: '#23262F'
        }}
      >
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 text-base font-bold tracking-tight hover:opacity-90 transition-opacity"
          >
            <span>Pi Vaani</span>
            <span className="text-[#FF5426] text-xs">●</span>
            <span className="text-sm font-medium text-[#8E95A5]">Demo</span>
          </Link>
          <span
            className="text-[11px] font-mono px-2 py-0.5 rounded border text-[#8E95A5]"
            style={{ backgroundColor: '#0A0B0F', borderColor: '#23262F' }}
          >
            STAGE 2 · LIVE SANDBOX
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-mono"
            style={{ backgroundColor: '#0A0B0F', borderColor: '#23262F' }}
          >
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isConnected ? 'bg-[#22C55E]' : 'bg-[#EF4444]'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isConnected ? 'bg-[#22C55E]' : 'bg-[#EF4444]'
                }`}
              />
            </span>
            <span className={isConnected ? 'text-[#22C55E] font-medium' : 'text-[#EF4444] font-medium'}>
              {isConnected ? 'Sandbox Connected' : 'Connecting to :8000...'}
            </span>
          </div>

          <button
            type="button"
            onClick={handleResetSandbox}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors hover:border-[#FF5426] hover:text-[#FF5426] cursor-pointer"
            style={{
              backgroundColor: '#14161C',
              borderColor: '#23262F',
              color: '#FAFAFA'
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </header>

      {/* MAIN DASHBOARD */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-[1600px] w-full mx-auto">
        {/* ======================================================== */}
        {/* 2. LEFT COLUMN (CUSTOMER PHONE)                         */}
        {/* ======================================================== */}
        <section
          className="lg:col-span-3 xl:col-span-3 flex flex-col items-center justify-start rounded-2xl p-5 border"
          style={{
            backgroundColor: '#14161C',
            borderColor: '#23262F'
          }}
        >
          <div className="w-full flex items-center justify-between mb-4 pb-2 border-b border-[#23262F]">
            <span className="text-xs font-mono uppercase tracking-wider text-[#8E95A5] flex items-center gap-1.5">
              <Smartphone className="w-3.5 h-3.5 text-[#FF5426]" />
              Customer Screen
            </span>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                paymentStatus === 'CONFIRMED'
                  ? 'bg-[#22C55E]/20 text-[#22C55E] border border-[#22C55E]/40'
                  : paymentStatus === 'PENDING'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse'
                  : 'bg-[#23262F] text-[#8E95A5]'
              }`}
            >
              {paymentStatus}
            </span>
          </div>

          {/* CSS-drawn phone frame */}
          <div
            className="w-[280px] sm:w-[290px] h-[540px] rounded-[38px] p-3 relative flex flex-col justify-between shadow-2xl border"
            style={{
              backgroundColor: '#0A0B0F',
              borderColor: '#23262F',
              boxShadow: '0 20px 40px -15px rgba(0,0,0,0.8), inset 0 0 0 1px rgba(255,255,255,0.04)'
            }}
          >
            {/* Phone Notch */}
            <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-20 h-4 bg-[#14161C] border border-[#23262F] rounded-full z-20 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-[#0A0B0F] mr-1.5"></div>
              <div className="w-1 h-1 rounded-full bg-[#2A2E39]"></div>
            </div>

            {/* Top Phone Bar */}
            <div className="pt-4 px-2 flex justify-between items-center text-[10px] font-mono text-[#8E95A5]">
              <span>12:04</span>
              <div className="flex items-center gap-1">
                <span>5G</span>
                <span>●</span>
                <span>100%</span>
              </div>
            </div>

            {/* Merchant info & payment action */}
            <div className="my-auto px-2 flex flex-col items-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3 border shadow-inner text-xl font-bold text-[#FF5426]"
                style={{
                  backgroundColor: '#14161C',
                  borderColor: '#23262F'
                }}
              >
                ☕
              </div>

              <h3 className="font-semibold text-lg text-white mb-0.5 tracking-tight">
                Ravi&apos;s Chai Stall
              </h3>
              <p className="text-xs text-[#8E95A5] font-mono mb-4">ravi.chai@upi</p>

              {/* Large Amount */}
              <div className="mb-4 flex flex-col items-center">
                <span className="text-[11px] font-mono uppercase tracking-widest text-[#8E95A5] mb-1">
                  Amount Payable
                </span>
                <span className="text-5xl font-black tracking-tight text-white flex items-baseline">
                  <span className="text-3xl mr-1 font-semibold text-[#8E95A5]">₹</span>40
                </span>
              </div>

              {/* Dynamic Status Pill */}
              {paymentStatus === 'PENDING' && (
                <div className="mb-3 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 animate-spin" />
                  <span>Stuck &gt; 2s · Bank Pending</span>
                </div>
              )}

              {paymentStatus === 'CONFIRMED' && (
                <div className="mb-3 px-3 py-1 rounded-full bg-[#22C55E]/10 border border-[#22C55E]/30 text-[#22C55E] text-xs font-mono flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Payment Confirmed</span>
                </div>
              )}

              {/* Primary Pay Button */}
              <button
                type="button"
                onClick={handleCustomerPay}
                disabled={paymentStatus === 'PROCESSING'}
                className={`w-full py-3.5 px-6 rounded-xl font-semibold text-white tracking-wide transition-all duration-150 transform active:translate-y-0 shadow-lg cursor-pointer flex items-center justify-center gap-2 ${
                  paymentStatus === 'PROCESSING'
                    ? 'bg-gray-600 opacity-70 cursor-not-allowed'
                    : paymentStatus === 'CONFIRMED'
                    ? 'bg-[#22C55E] hover:bg-[#1eb354]'
                    : paymentStatus === 'PENDING'
                    ? 'bg-amber-600 hover:bg-amber-500'
                    : 'bg-[#FF5426] hover:bg-[#ff683d] hover:-translate-y-0.5'
                }`}
                style={{
                  boxShadow:
                    paymentStatus === 'CONFIRMED'
                      ? '0 4px 18px rgba(34, 197, 94, 0.35)'
                      : '0 4px 18px rgba(255, 84, 38, 0.35)'
                }}
              >
                {paymentStatus === 'PROCESSING' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : paymentStatus === 'CONFIRMED' ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Paid ₹40 ✓</span>
                  </>
                ) : paymentStatus === 'PENDING' ? (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    <span>Pay Again (Retap)</span>
                  </>
                ) : (
                  <span>Pay ₹40</span>
                )}
              </button>
            </div>

            {/* Customer Captions Area */}
            <div
              className={`w-full min-h-[96px] rounded-2xl p-3 border border-dashed flex flex-col items-center justify-center text-center transition-all ${
                paymentStatus === 'PENDING'
                  ? 'border-amber-500/40 bg-amber-500/5'
                  : paymentStatus === 'CONFIRMED'
                  ? 'border-[#22C55E]/40 bg-[#22C55E]/5'
                  : 'border-[#23262F] bg-[#14161C]/70'
              }`}
            >
              <Volume2
                className={`w-4 h-4 mb-1.5 ${
                  paymentStatus === 'CONFIRMED'
                    ? 'text-[#22C55E]'
                    : paymentStatus === 'PENDING'
                    ? 'text-amber-400'
                    : 'text-[#8E95A5]'
                }`}
              />
              <p className="text-xs text-[#FAFAFA] font-mono leading-snug">
                {customerCaption}
              </p>
            </div>

            {/* Bottom Home Indicator */}
            <div className="w-24 h-1 bg-[#23262F] rounded-full mx-auto mt-2"></div>
          </div>
        </section>

        {/* ======================================================== */}
        {/* 3. CENTER COLUMN (VIRTUAL SOUNDBOX)                      */}
        {/* ======================================================== */}
        <section
          className="lg:col-span-5 xl:col-span-5 flex flex-col items-center justify-between rounded-2xl p-6 border"
          style={{
            backgroundColor: '#14161C',
            borderColor: '#23262F'
          }}
        >
          <div className="w-full flex items-center justify-between pb-3 border-b border-[#23262F]">
            <span className="text-xs font-mono uppercase tracking-wider text-[#8E95A5] flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-[#FF5426]" />
              Virtual Soundbox Emulator
            </span>
            <span
              className={`flex items-center gap-1.5 text-[11px] font-mono ${
                activeCase
                  ? 'text-amber-400'
                  : paymentStatus === 'CONFIRMED'
                  ? 'text-[#22C55E]'
                  : 'text-[#8E95A5]'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  activeCase
                    ? 'bg-amber-400 animate-ping'
                    : paymentStatus === 'CONFIRMED'
                    ? 'bg-[#22C55E]'
                    : 'bg-[#2A2E39]'
                }`}
              />
              {activeCase ? 'CASE ACTIVE' : paymentStatus === 'CONFIRMED' ? 'SETTLED' : 'IDLE'}
            </span>
          </div>

          {/* Soundbox Physical Speaker Visual */}
          <div className="my-auto py-6 flex flex-col items-center w-full max-w-[380px]">
            <div
              className="w-full aspect-[1/1] max-w-[340px] rounded-[44px] p-7 border relative flex flex-col items-center justify-between shadow-2xl transition-all"
              style={{
                background: 'linear-gradient(145deg, #181A22 0%, #0E1015 100%)',
                borderColor: activeCase ? '#f59e0b' : '#23262F',
                boxShadow: activeCase
                  ? '0 0 35px rgba(245, 158, 11, 0.25), 0 25px 60px -12px rgba(0,0,0,0.9)'
                  : '0 25px 60px -12px rgba(0,0,0,0.9), inset 0 1px 1px rgba(255,255,255,0.06)'
              }}
            >
              <div className="text-center">
                <h2 className="text-xl font-extrabold tracking-tight text-white">Pi Vaani</h2>
                <p className="text-[10px] font-mono tracking-widest uppercase text-[#8E95A5] mt-0.5">
                  BHAROSA SOUNDBOX
                </p>
              </div>

              {/* Speaker Grille Accent & Ring LED Container */}
              <div className="relative flex items-center justify-center my-auto">
                <div
                  className="w-48 h-48 rounded-full flex items-center justify-center border border-[#23262F]/50 p-2"
                  style={{
                    backgroundImage: 'radial-gradient(#2A2E39 1px, transparent 1px)',
                    backgroundSize: '8px 8px'
                  }}
                >
                  {/* Dynamic Ring LED */}
                  <div
                    className={`w-36 h-36 rounded-full border-[5px] flex items-center justify-center transition-all duration-300 relative ${
                      isMicPressed
                        ? 'border-[#FF5426] shadow-[0_0_24px_rgba(255,84,38,0.5)]'
                        : activeCase
                        ? 'border-amber-400 shadow-[0_0_24px_rgba(245,158,11,0.5)] animate-pulse'
                        : paymentStatus === 'CONFIRMED'
                        ? 'border-[#22C55E] shadow-[0_0_20px_rgba(34,197,94,0.4)]'
                        : 'border-[#2A2E39] shadow-[inset_0_2px_8px_rgba(0,0,0,0.6)]'
                    }`}
                    style={{ backgroundColor: '#14161C' }}
                  >
                    <button
                      type="button"
                      onMouseDown={() => setIsMicPressed(true)}
                      onMouseUp={() => setIsMicPressed(false)}
                      onTouchStart={() => setIsMicPressed(true)}
                      onTouchEnd={() => setIsMicPressed(false)}
                      className={`w-24 h-24 rounded-full flex flex-col items-center justify-center gap-1 transition-all transform active:scale-95 cursor-pointer shadow-lg ${
                        isMicPressed
                          ? 'bg-[#FF5426] text-white shadow-[0_0_20px_rgba(255,84,38,0.6)]'
                          : 'bg-[#1C1F28] hover:bg-[#232733] text-[#FAFAFA] border border-[#2A2E39]'
                      }`}
                    >
                      <Mic className={`w-7 h-7 ${isMicPressed ? 'scale-110' : ''} transition-transform`} />
                      <span className="text-[10px] font-semibold tracking-wide uppercase">
                        {isMicPressed ? 'Listening...' : 'Hold to Talk'}
                      </span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Status Display */}
              <div className="w-full flex items-center justify-between px-2 pt-2 border-t border-[#23262F]/60 text-[11px] font-mono">
                <span className="text-[#8E95A5]">DUAL MIC ARRAY</span>
                <span
                  className={
                    activeCase
                      ? 'text-amber-400 font-bold'
                      : paymentStatus === 'CONFIRMED'
                      ? 'text-[#22C55E] font-bold'
                      : 'text-[#8E95A5]'
                  }
                >
                  {activeCase
                    ? `INCIDENT ${activeCase.id}`
                    : paymentStatus === 'CONFIRMED'
                    ? '₹40 RECEIVED'
                    : 'STANDBY'}
                </span>
              </div>
            </div>
          </div>

          {/* Text Input Box */}
          <div className="w-full mt-4">
            <div
              className="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all focus-within:border-[#FF5426]"
              style={{
                backgroundColor: '#0A0B0F',
                borderColor: '#23262F'
              }}
            >
              <Terminal className="w-4 h-4 text-[#8E95A5] shrink-0" />
              <input
                type="text"
                value={commandText}
                onChange={(e) => setCommandText(e.target.value)}
                placeholder="Type command (e.g. 'Careful rakho', 'Refund ₹40')..."
                className="w-full bg-transparent text-sm text-[#FAFAFA] placeholder-[#8E95A5] focus:outline-none font-mono"
              />
              <button
                type="button"
                className="p-1.5 rounded-lg text-[#8E95A5] hover:text-[#FF5426] hover:bg-[#14161C] transition-colors"
                title="Send command"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] font-mono text-[#8E95A5] mt-1.5 px-1">
              Press &quot;C&quot; key to open Control Drawer · Test pending payments and forced webhooks.
            </p>
          </div>
        </section>

        {/* ======================================================== */}
        {/* 4. RIGHT COLUMN (MERCHANT PANEL)                         */}
        {/* ======================================================== */}
        <section
          className="lg:col-span-4 xl:col-span-4 flex flex-col gap-4 rounded-2xl p-5 border"
          style={{
            backgroundColor: '#14161C',
            borderColor: '#23262F'
          }}
        >
          <div className="flex items-center justify-between pb-2 border-b border-[#23262F]">
            <span className="text-xs font-mono uppercase tracking-wider text-[#8E95A5] flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-[#FF5426]" />
              Merchant Trust Dial
            </span>
            <span className="text-[10px] font-mono text-[#8E95A5]">VOICE & PIN GUARD</span>
          </div>

          {/* Row of Three Toggle Chips */}
          <div>
            <label className="text-[11px] font-mono text-[#8E95A5] block mb-2">
              ACTIVE SAFETY MODE
            </label>
            <div
              className="grid grid-cols-3 gap-1.5 p-1 rounded-xl border"
              style={{
                backgroundColor: '#0A0B0F',
                borderColor: '#23262F'
              }}
            >
              {['Careful', 'Balanced', 'Fast'].map((mode) => {
                const isActive = dialMode === mode
                return (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => handleDialChange(mode)}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                      isActive
                        ? 'bg-[#FF5426] text-white shadow-md'
                        : 'text-[#8E95A5] hover:text-white hover:bg-[#14161C]'
                    }`}
                  >
                    {mode}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Dynamic Case Card */}
          <div
            className={`rounded-xl p-4 border transition-all ${
              activeCase
                ? 'border-amber-500/50 bg-amber-500/5 shadow-[0_0_20px_rgba(245,158,11,0.15)]'
                : 'border-[#23262F] bg-[#0A0B0F]'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#8E95A5] uppercase tracking-wider">
                Incident Case Card
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  activeCase
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse font-bold'
                    : 'bg-[#14161C] text-[#8E95A5] border-[#23262F]'
                }`}
              >
                {activeCase ? 'STATUS: OPEN' : 'STANDBY'}
              </span>
            </div>

            {activeCase ? (
              <div className="py-2 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                    <div>
                      <h4 className="text-base font-bold text-white tracking-tight">
                        Case {activeCase.id}
                      </h4>
                      <p className="text-[11px] font-mono text-amber-400">
                        {activeCase.trigger_reason}
                      </p>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-white">
                    ₹{activeCase.amount || 40}
                  </span>
                </div>

                <div className="pt-2 border-t border-[#23262F] flex items-center justify-between text-[11px] font-mono text-[#8E95A5]">
                  <span>Payer: {activeCase.payer_vpa || 'customer@upi'}</span>
                  <button
                    type="button"
                    onClick={handleForceSuccess}
                    className="text-xs text-[#22C55E] hover:underline cursor-pointer"
                  >
                    Resolve (Confirm) →
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-5 flex flex-col items-center justify-center text-center">
                <Shield className="w-8 h-8 text-[#8E95A5] mb-2 opacity-50" />
                <p className="text-sm font-semibold text-white">No Active Case</p>
                <p className="text-xs text-[#8E95A5] font-mono mt-0.5">
                  Waiting for stuck payment trigger...
                </p>
              </div>
            )}
          </div>

          {/* 7-Gate Evaluation Panel */}
          <div
            className="flex-1 rounded-xl p-4 border flex flex-col"
            style={{
              backgroundColor: '#0A0B0F',
              borderColor: '#23262F'
            }}
          >
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#23262F]">
              <span className="text-xs font-mono text-[#8E95A5] uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#22C55E]" />
                7-Gate Evaluation Panel
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5]">
                {activeCase ? 'EVALUATING' : 'ALL IDLE'}
              </span>
            </div>

            <div className="space-y-2.5 flex-1 flex flex-col justify-around">
              {gates.map((gate, index) => {
                // If a case is active, simulate gate status
                const isPassed = activeCase && index < 4
                const isEvaluating = activeCase && index === 4
                return (
                  <div
                    key={gate.name}
                    className="flex items-center justify-between py-1.5 px-2.5 rounded-lg border transition-colors hover:border-[#3A3F4D]"
                    style={{
                      backgroundColor: '#14161C',
                      borderColor: '#23262F'
                    }}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="text-[10px] font-mono text-[#8E95A5] w-3.5">
                        0{index + 1}
                      </span>
                      <div>
                        <p className="text-xs font-medium text-white leading-tight">{gate.name}</p>
                        <p className="text-[10px] font-mono text-[#8E95A5] leading-none mt-0.5">
                          {gate.desc}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span
                        className={`w-3 h-3 rounded-full border transition-all ${
                          isPassed
                            ? 'bg-[#22C55E] border-[#22C55E] shadow-[0_0_8px_#22C55E]'
                            : isEvaluating
                            ? 'bg-amber-400 border-amber-400 shadow-[0_0_8px_#f59e0b] animate-ping'
                            : 'bg-[#2A2E39] border-[#3A3F4D]'
                        }`}
                        title={isPassed ? 'Passed' : isEvaluating ? 'Evaluating' : 'Idle'}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      </main>

      {/* ======================================================== */}
      {/* 5. BOTTOM ROW (AUDIT TRAIL)                             */}
      {/* ======================================================== */}
      <footer
        className="w-full border-t p-4 z-20 shrink-0"
        style={{
          backgroundColor: '#14161C',
          borderColor: '#23262F'
        }}
      >
        <div className="max-w-[1600px] mx-auto flex flex-col gap-2">
          <div className="flex items-center justify-between pb-2 border-b border-[#23262F]">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#FF5426]" />
              <h4 className="text-xs font-mono font-bold tracking-wider uppercase text-white">
                Audit Trail
              </h4>
              <span
                className="text-[10px] font-mono px-2 py-0.5 rounded border text-[#8E95A5] hidden sm:inline-block"
                style={{ backgroundColor: '#0A0B0F', borderColor: '#23262F' }}
              >
                SHA-256 IMMUTABLE CHAIN
              </span>
            </div>

            <div className="flex items-center gap-3">
              {verifyResult && (
                <span
                  className={`text-xs font-mono px-2.5 py-1 rounded border animate-fade-in ${
                    verifyResult.valid
                      ? 'bg-[#22C55E]/10 border-[#22C55E]/30 text-[#22C55E]'
                      : 'bg-red-500/10 border-red-500/30 text-red-400'
                  }`}
                >
                  {verifyResult.message || (verifyResult.valid ? 'Chain Verified' : 'Corrupted')}
                </span>
              )}

              <button
                type="button"
                onClick={handleVerifyIntegrity}
                disabled={isVerifying}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg border transition-colors hover:border-[#22C55E] hover:text-[#22C55E] cursor-pointer"
                style={{
                  backgroundColor: '#0A0B0F',
                  borderColor: '#23262F',
                  color: '#FAFAFA'
                }}
              >
                {isVerifying ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5 text-[#22C55E]" />
                )}
                <span>Verify Integrity</span>
              </button>

              <button
                type="button"
                onClick={() => setIsDrawerOpen((prev) => !prev)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg border text-[#8E95A5] hover:text-white transition-colors cursor-pointer"
                style={{
                  backgroundColor: '#0A0B0F',
                  borderColor: '#23262F'
                }}
                title="Toggle Control Drawer"
              >
                <ChevronUp
                  className={`w-3.5 h-3.5 transition-transform ${isDrawerOpen ? 'rotate-180' : ''}`}
                />
                <span>Control Drawer [C]</span>
              </button>
            </div>
          </div>

          {/* Scrolling terminal-style log */}
          <div
            className="w-full h-24 rounded-lg p-3 font-mono text-xs overflow-y-auto space-y-1.5 border"
            style={{
              backgroundColor: '#0A0B0F',
              borderColor: '#23262F'
            }}
          >
            {logs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 text-xs leading-relaxed">
                <span className="text-[#8E95A5]">[{log.time}]</span>
                <span
                  className={`font-semibold ${
                    log.tag === 'firewall'
                      ? 'text-amber-400'
                      : log.tag === 'webhook' || log.tag === 'audit'
                      ? 'text-[#22C55E]'
                      : log.tag === 'customer'
                      ? 'text-[#FF5426]'
                      : 'text-[#8E95A5]'
                  }`}
                >
                  {log.tag}:
                </span>
                <span className="text-[#E2E8F0]">{log.text}</span>
              </div>
            ))}
          </div>
        </div>
      </footer>

      {/* ======================================================== */}
      {/* 6. CONTROL DRAWER (Stage 2 Scenario Injection)          */}
      {/* ======================================================== */}
      {isDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 transition-opacity"
          onClick={() => setIsDrawerOpen(false)}
        />
      )}

      <div
        className={`fixed bottom-0 left-0 right-0 z-50 border-t shadow-2xl transition-transform duration-300 ease-out transform ${
          isDrawerOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{
          backgroundColor: '#14161C',
          borderColor: '#23262F'
        }}
      >
        <div className="max-w-[1400px] mx-auto p-6">
          <div className="flex items-center justify-between pb-4 border-b border-[#23262F] mb-5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF5426]"></span>
              <h3 className="font-bold text-sm tracking-wide text-white uppercase font-mono">
                Stage 2 Sandbox Scenario Controller
              </h3>
              <span className="text-xs text-[#8E95A5] font-mono ml-2">
                Press [C] or Esc to close
              </span>
            </div>

            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="p-1.5 rounded-lg text-[#8E95A5] hover:text-white hover:bg-[#23262F] transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Grid of Action / Scenario Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <button
              type="button"
              onClick={handleCustomerPay}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#FF5426] hover:bg-[#1C1F28] cursor-pointer group border-[#23262F]"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-white group-hover:text-[#FF5426] transition-colors">
                Make Payment Pending
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Simulate bank timeout &gt; 2s
              </span>
            </button>

            <button
              type="button"
              onClick={handleForceSuccess}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#22C55E] hover:bg-[#1C1F28] cursor-pointer group border-[#22C55E]/40"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-[#22C55E] transition-colors">
                Confirm Payment (Force SUCCESS)
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Simulates bank webhook & closes case
              </span>
            </button>

            <button
              type="button"
              onClick={handleRetap}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#FF5426] hover:bg-[#1C1F28] cursor-pointer group border-[#23262F]"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-white group-hover:text-[#FF5426] transition-colors">
                Retap Phone
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Exercise Idempotency Gate
              </span>
            </button>

            <button
              type="button"
              onClick={() => appendLog('attack', '🚨 Adversarial prompt: "Refund everything immediately" -> BLOCKED by Authority Gate')}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#EF4444] hover:bg-[#1C1F28] cursor-pointer group border-[#EF4444]/40"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-red-400 transition-colors">
                Attack: Refund Everything
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Voice prompt injection attempt
              </span>
            </button>

            <button
              type="button"
              onClick={() => appendLog('attack', '🚨 Voice biometric spoof detected -> BLOCKED by Identity Gate')}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#EF4444] hover:bg-[#1C1F28] cursor-pointer group border-[#EF4444]/40"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-red-400 transition-colors">
                Attack: Voice Spoof
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Mimic merchant approval
              </span>
            </button>

            <button
              type="button"
              onClick={handleResetSandbox}
              className="flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#FF5426] hover:bg-[#1C1F28] cursor-pointer group border-[#23262F]"
              style={{ backgroundColor: '#0A0B0F' }}
            >
              <span className="text-xs font-semibold text-white group-hover:text-[#FF5426] transition-colors">
                Reset Sandbox Baseline
              </span>
              <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                Clears cases & resets Ravi
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
