'use client'

import React, { useState, useEffect } from 'react'
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
  AlertCircle,
  Hash
} from 'lucide-react'

export default function Demo() {
  // Toggle states & drawer
  const [dialMode, setDialMode] = useState('Balanced') // 'Careful' | 'Balanced' | 'Fast'
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [commandText, setCommandText] = useState('')
  const [isMicPressed, setIsMicPressed] = useState(false)

  // Listen for 'C' key to toggle the control drawer
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if typing in an input or textarea
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return
      }
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

  const gates = [
    { name: 'Authority', desc: 'Signer verification & channel origin' },
    { name: 'Amount', desc: 'Threshold check within merchant bounds' },
    { name: 'Confidence', desc: 'Acoustic & intent certainty threshold' },
    { name: 'Identity', desc: 'Voice biometric & payer alignment' },
    { name: 'Idempotency', desc: 'Duplicate suppression within 2s window' },
    { name: 'Reversibility', desc: 'Escrow buffer before settlement' },
    { name: 'Approval', desc: 'Merchant vocal confirmation if required' }
  ]

  const fakeLogs = [
    { time: '12:04:31', tag: 'system', text: 'App loaded' },
    { time: '12:04:32', tag: 'firewall', text: 'Idle' },
    { time: '12:04:32', tag: 'soundbox', text: 'Hardware interface connected · Mock ready' }
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
        {/* Left Side: Brand & Demo Title */}
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
            BHAROSA SHELL
          </span>
        </div>

        {/* Right Side: Status dot & Reset button */}
        <div className="flex items-center gap-4">
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-mono"
            style={{ backgroundColor: '#0A0B0F', borderColor: '#23262F' }}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22C55E] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#22C55E]"></span>
            </span>
            <span className="text-[#22C55E] font-medium">Sandbox Connected</span>
          </div>

          <button
            type="button"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors hover:border-[#FF5426] hover:text-[#FF5426]"
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

      {/* MAIN DASHBOARD: 3 COLUMNS */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-[1600px] w-full mx-auto">
        {/* ======================================================== */}
        {/* 2. LEFT COLUMN (CUSTOMER PHONE) - 3.5 cols on desktop    */}
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
            <span className="text-[10px] font-mono text-[#8E95A5]">UPI 2.0</span>
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

            {/* Merchant info & payment card */}
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
              <p className="text-xs text-[#8E95A5] font-mono mb-6">ravi.chai@upi</p>

              {/* Large Amount */}
              <div className="mb-6 flex flex-col items-center">
                <span className="text-[11px] font-mono uppercase tracking-widest text-[#8E95A5] mb-1">
                  Amount Payable
                </span>
                <span className="text-5xl font-black tracking-tight text-white flex items-baseline">
                  <span className="text-3xl mr-1 font-semibold text-[#8E95A5]">₹</span>40
                </span>
              </div>

              {/* Primary Pay Button */}
              <button
                type="button"
                className="w-full py-3.5 px-6 rounded-xl font-semibold text-white tracking-wide transition-all duration-150 transform hover:-translate-y-0.5 active:translate-y-0 shadow-lg cursor-pointer"
                style={{
                  backgroundColor: '#FF5426',
                  boxShadow: '0 4px 18px rgba(255, 84, 38, 0.35)'
                }}
              >
                Pay ₹40
              </button>
            </div>

            {/* Customer Captions Area */}
            <div
              className="w-full min-h-[96px] rounded-2xl p-3 border border-dashed flex flex-col items-center justify-center text-center transition-all"
              style={{
                backgroundColor: 'rgba(20, 22, 28, 0.7)',
                borderColor: '#23262F'
              }}
            >
              <Volume2 className="w-4 h-4 text-[#8E95A5] mb-1.5 opacity-60" />
              <p className="text-xs text-[#8E95A5] font-mono italic leading-snug">
                Customer Captions will appear here
              </p>
            </div>

            {/* Bottom Home Indicator */}
            <div className="w-24 h-1 bg-[#23262F] rounded-full mx-auto mt-2"></div>
          </div>
        </section>

        {/* ======================================================== */}
        {/* 3. CENTER COLUMN (VIRTUAL SOUNDBOX) - 5.5 cols on desktop */}
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
            <span className="flex items-center gap-1 text-[11px] font-mono text-[#8E95A5]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#8E95A5]"></span>
              IDLE
            </span>
          </div>

          {/* Soundbox Physical Speaker Visual */}
          <div className="my-auto py-6 flex flex-col items-center w-full max-w-[380px]">
            <div
              className="w-full aspect-[1/1] max-w-[340px] rounded-[44px] p-7 border relative flex flex-col items-center justify-between shadow-2xl transition-all"
              style={{
                background: 'linear-gradient(145deg, #181A22 0%, #0E1015 100%)',
                borderColor: '#23262F',
                boxShadow: '0 25px 60px -12px rgba(0,0,0,0.9), inset 0 1px 1px rgba(255,255,255,0.06)'
              }}
            >
              {/* Soundbox Top Header */}
              <div className="text-center">
                <h2 className="text-xl font-extrabold tracking-tight text-white">Pi Vaani</h2>
                <p className="text-[10px] font-mono tracking-widest uppercase text-[#8E95A5] mt-0.5">
                  BHAROSA SOUNDBOX
                </p>
              </div>

              {/* Speaker Grille Accent & Ring LED Container */}
              <div className="relative flex items-center justify-center my-auto">
                {/* Acoustic grille dots background ring */}
                <div
                  className="w-48 h-48 rounded-full flex items-center justify-center border border-[#23262F]/50 p-2"
                  style={{
                    backgroundImage: 'radial-gradient(#2A2E39 1px, transparent 1px)',
                    backgroundSize: '8px 8px'
                  }}
                >
                  {/* Ring LED (grey/idle state) */}
                  <div
                    className={`w-36 h-36 rounded-full border-[5px] flex items-center justify-center transition-all duration-300 relative ${
                      isMicPressed
                        ? 'border-[#FF5426] shadow-[0_0_24px_rgba(255,84,38,0.45)]'
                        : 'border-[#2A2E39] shadow-[inset_0_2px_8px_rgba(0,0,0,0.6)]'
                    }`}
                    style={{ backgroundColor: '#14161C' }}
                  >
                    {/* Ring LED idle pulse hint */}
                    <div className="absolute inset-1 rounded-full border border-white/5 pointer-events-none" />

                    {/* Large "Hold to Talk" mic button */}
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

              {/* Soundbox Foot / Status Indicator */}
              <div className="w-full flex items-center justify-between px-2 pt-2 border-t border-[#23262F]/60 text-[11px] font-mono text-[#8E95A5]">
                <span>DUAL MIC ARRAY</span>
                <span className="flex items-center gap-1.5 text-xs text-[#8E95A5]">
                  <span className="w-2 h-2 rounded-full bg-[#2A2E39]"></span>
                  STANDBY
                </span>
              </div>
            </div>
          </div>

          {/* Text Input Box: Type command... */}
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
                placeholder="Type command..."
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
              Tip: Press &quot;C&quot; on your keyboard to reveal the Sandbox Scenario Drawer.
            </p>
          </div>
        </section>

        {/* ======================================================== */}
        {/* 4. RIGHT COLUMN (MERCHANT PANEL) - 3.5 cols on desktop   */}
        {/* ======================================================== */}
        <section
          className="lg:col-span-4 xl:col-span-4 flex flex-col gap-4 rounded-2xl p-5 border"
          style={{
            backgroundColor: '#14161C',
            borderColor: '#23262F'
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-[#23262F]">
            <span className="text-xs font-mono uppercase tracking-wider text-[#8E95A5] flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-[#FF5426]" />
              Merchant Trust Dial
            </span>
            <span className="text-[10px] font-mono text-[#8E95A5]">VOICE-CONTROLLED</span>
          </div>

          {/* Row of Three Toggle Chips: Careful, Balanced, Fast */}
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
                    onClick={() => setDialMode(mode)}
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

          {/* Case Card: No Active Case */}
          <div
            className="rounded-xl p-4 border flex flex-col justify-between"
            style={{
              backgroundColor: '#0A0B0F',
              borderColor: '#23262F'
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#8E95A5] uppercase tracking-wider">
                Incident Case Card
              </span>
              <span
                className="text-[10px] font-mono px-2 py-0.5 rounded border text-[#8E95A5]"
                style={{ backgroundColor: '#14161C', borderColor: '#23262F' }}
              >
                STANDBY
              </span>
            </div>

            <div className="py-5 flex flex-col items-center justify-center text-center">
              <Shield className="w-8 h-8 text-[#8E95A5] mb-2 opacity-50" />
              <p className="text-sm font-semibold text-white">No Active Case</p>
              <p className="text-xs text-[#8E95A5] font-mono mt-0.5">
                Waiting for stuck payment trigger...
              </p>
            </div>
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
              <span className="text-[10px] font-mono text-[#8E95A5]">ALL IDLE</span>
            </div>

            {/* Vertical list of 7 rows */}
            <div className="space-y-2.5 flex-1 flex flex-col justify-around">
              {gates.map((gate, index) => (
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

                  {/* Grey circle (idle state) */}
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded-full border"
                      style={{
                        backgroundColor: '#2A2E39',
                        borderColor: '#3A3F4D'
                      }}
                      title="Idle State"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* ======================================================== */}
      {/* 5. BOTTOM ROW (AUDIT TRAIL) - Full Width                 */}
      {/* ======================================================== */}
      <footer
        className="w-full border-t p-4 z-20 shrink-0"
        style={{
          backgroundColor: '#14161C',
          borderColor: '#23262F'
        }}
      >
        <div className="max-w-[1600px] mx-auto flex flex-col gap-2">
          {/* Header row */}
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
                SHA-256 IMMUTABLE LOG
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg border transition-colors hover:border-[#22C55E] hover:text-[#22C55E]"
                style={{
                  backgroundColor: '#0A0B0F',
                  borderColor: '#23262F',
                  color: '#FAFAFA'
                }}
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#22C55E]" />
                <span>Verify Integrity</span>
              </button>

              <button
                type="button"
                onClick={() => setIsDrawerOpen((prev) => !prev)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg border text-[#8E95A5] hover:text-white transition-colors"
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
            {fakeLogs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 text-xs leading-relaxed">
                <span className="text-[#8E95A5]">[{log.time}]</span>
                <span
                  className={`font-semibold ${
                    log.tag === 'firewall'
                      ? 'text-[#22C55E]'
                      : log.tag === 'soundbox'
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
      {/* 6. CONTROL DRAWER - Slides up when pressing C key       */}
      {/* ======================================================== */}
      {/* Backdrop */}
      {isDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 transition-opacity"
          onClick={() => setIsDrawerOpen(false)}
        />
      )}

      {/* Drawer Container */}
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
          {/* Drawer Header */}
          <div className="flex items-center justify-between pb-4 border-b border-[#23262F] mb-5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF5426]"></span>
              <h3 className="font-bold text-sm tracking-wide text-white uppercase font-mono">
                Sandbox Scenario Controller
              </h3>
              <span className="text-xs text-[#8E95A5] font-mono ml-2">
                Press [C] or Esc to close
              </span>
            </div>

            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="p-1.5 rounded-lg text-[#8E95A5] hover:text-white hover:bg-[#23262F] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Grid of Action / Scenario Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {[
              { label: 'Make Payment Pending', desc: 'Simulate timeout > 2s', color: 'border-[#23262F]' },
              { label: 'Retap', desc: 'Customer taps phone again', color: 'border-[#23262F]' },
              { label: 'Confirm Payment', desc: 'Webhook success sync', color: 'border-[#22C55E]/40' },
              { label: 'Attack: Refund Everything', desc: 'Adversarial voice prompt', color: 'border-[#EF4444]/40' },
              { label: 'Attack: Voice Spoof', desc: 'Unauthorized speaker mimic', color: 'border-[#EF4444]/40' },
              { label: 'Attack: Prompt Injection', desc: 'System override jailbreak', color: 'border-[#EF4444]/40' },
              { label: 'Simulate Network Drop', desc: 'NPCI gateway failure', color: 'border-[#23262F]' },
              { label: 'Force Voice Approval', desc: 'Require merchant PIN/voice', color: 'border-[#23262F]' },
              { label: 'Reset Sandbox State', desc: 'Clear all mocks & caches', color: 'border-[#23262F]' }
            ].map((btn, index) => (
              <button
                key={index}
                type="button"
                className={`flex flex-col items-start p-3 rounded-xl border text-left transition-all hover:border-[#FF5426] hover:bg-[#1C1F28] cursor-pointer group ${btn.color}`}
                style={{ backgroundColor: '#0A0B0F' }}
              >
                <span className="text-xs font-semibold text-white group-hover:text-[#FF5426] transition-colors">
                  {btn.label}
                </span>
                <span className="text-[10px] font-mono text-[#8E95A5] mt-1 leading-tight">
                  {btn.desc}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

