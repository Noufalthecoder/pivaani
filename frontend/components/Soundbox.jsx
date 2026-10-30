'use client'

import React, { useMemo } from 'react'
import { Mic, Square } from 'lucide-react'

// LED / LCD accent per device state
const TONES = {
  idle: { ring: '#CBD5E1', glow: 'transparent', lcd: '#7DD3FC' },
  listening: { ring: '#FF5426', glow: 'rgba(255,84,38,0.55)', lcd: '#FDBA74' },
  case: { ring: '#F59E0B', glow: 'rgba(245,158,11,0.55)', lcd: '#FCD34D' },
  speaking: { ring: '#22C55E', glow: 'rgba(34,197,94,0.55)', lcd: '#86EFAC' },
  blocked: { ring: '#EF4444', glow: 'rgba(239,68,68,0.55)', lcd: '#FCA5A5' },
  confirmed: { ring: '#22C55E', glow: 'rgba(34,197,94,0.35)', lcd: '#86EFAC' }
}

// Decorative 21x21 QR-style pattern with the three finder squares
function useQrCells() {
  return useMemo(() => {
    const size = 21
    const finder = (r, c) =>
      [[0, 0], [0, 14], [14, 0]].some(([fr, fc]) => {
        const y = r - fr
        const x = c - fc
        if (y < 0 || y > 6 || x < 0 || x > 6) return null
        return y === 0 || y === 6 || x === 0 || x === 6 || (y >= 2 && y <= 4 && x >= 2 && x <= 4)
      })
    const inFinderZone = (r, c) => [[0, 0], [0, 14], [14, 0]].some(([fr, fc]) => r - fr >= -1 && r - fr <= 7 && c - fc >= -1 && c - fc <= 7)
    const cells = []
    let seed = 7
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        seed = (seed * 1103515245 + 12345) % 2147483648
        cells.push(inFinderZone(r, c) ? finder(r, c) : seed % 7 < 3)
      }
    }
    return cells
  }, [])
}

/**
 * Counter UPI soundbox: speaker grille inside a status LED ring, backlit LCD,
 * and physical buttons (hold-to-talk mic, stop voice).
 */
export default function Soundbox({
  tone = 'idle',
  speaking = false,
  lcdMain,
  lcdSub,
  isMicPressed,
  canStop,
  onMicDown,
  onMicUp,
  onStop
}) {
  const t = TONES[tone] || TONES.idle
  const qr = useQrCells()

  return (
    <div className="relative flex items-end justify-center gap-0 select-none">
      {/* QR standee behind the device */}
      <div
        className="hidden sm:flex -mr-2 mb-8 w-[150px] h-[214px] rounded-2xl bg-white border border-[#E2E8F0] flex-col items-center p-3 shadow-[0_18px_40px_-20px_rgba(15,23,42,0.35)] rotate-[-5deg]"
        aria-hidden="true"
      >
        <p className="text-[10px] font-bold uppercase tracking-widest text-[#FF5426]">Scan &amp; Pay</p>
        <div className="mt-2 grid grid-cols-[repeat(21,1fr)] w-[110px] h-[110px] p-1 bg-white">
          {qr.map((on, i) => (
            <span key={i} className={on ? 'bg-[#0F172A]' : 'bg-transparent'} />
          ))}
        </div>
        <p className="mt-2 text-[11px] font-semibold text-[#0F172A]">Ravi&apos;s Chai Stall</p>
        <p className="text-[10px] text-[#64748B]">ravi.chai@upi</p>
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Device body */}
        <div
          className="relative w-[290px] rounded-[42px] px-6 pt-5 pb-6 flex flex-col items-center border"
          style={{
            background: 'linear-gradient(170deg, #FFFFFF 0%, #F1F4F8 55%, #DCE2EA 100%)',
            borderColor: '#D3DAE4',
            boxShadow:
              '0 34px 60px -28px rgba(15,23,42,0.55), inset 0 2px 0 rgba(255,255,255,0.9), inset 0 -6px 14px rgba(148,163,184,0.35)'
          }}
        >
          {/* Brand plate + status LEDs */}
          <div className="w-full flex items-center justify-between">
            <div>
              <p className="text-[17px] font-extrabold tracking-tight text-[#0F172A] leading-none">Pi Vaani</p>
              <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-[#64748B] mt-1">UPI Soundbox</p>
            </div>
            <div className="flex items-center gap-1.5" title="4G · Battery">
              <span className="text-[9px] font-bold text-[#64748B]">4G</span>
              <span className="w-2 h-2 rounded-full bg-[#22C55E] shadow-[0_0_6px_#22C55E]" />
              <span className="w-2 h-2 rounded-full" style={{ background: t.ring, boxShadow: `0 0 6px ${t.glow}` }} />
            </div>
          </div>

          {/* Speaker grille inside the LED ring */}
          <div className="relative mt-4 w-[208px] h-[208px] flex items-center justify-center">
            {speaking && (
              <>
                <span className="absolute inset-0 rounded-full animate-ping" style={{ border: `3px solid ${t.ring}`, opacity: 0.35 }} />
                <span
                  className="absolute -inset-3 rounded-full animate-ping"
                  style={{ border: `2px solid ${t.ring}`, opacity: 0.2, animationDelay: '0.35s' }}
                />
              </>
            )}
            <div
              className={`absolute inset-0 rounded-full transition-all duration-300 ${tone === 'case' && !speaking ? 'animate-pulse' : ''}`}
              style={{ border: `7px solid ${t.ring}`, boxShadow: `0 0 28px ${t.glow}` }}
            />
            <div
              className="w-[180px] h-[180px] rounded-full"
              style={{
                backgroundColor: '#1E2430',
                backgroundImage: 'radial-gradient(#4A5465 1.5px, transparent 1.8px)',
                backgroundSize: '9px 9px',
                boxShadow: 'inset 0 6px 18px rgba(0,0,0,0.7), 0 2px 0 rgba(255,255,255,0.8)'
              }}
            />
          </div>

          {/* Backlit LCD */}
          <div
            className="mt-5 w-full h-[66px] rounded-xl px-4 flex flex-col justify-center"
            style={{ backgroundColor: '#0B1220', boxShadow: 'inset 0 3px 10px rgba(0,0,0,0.8), 0 1px 0 rgba(255,255,255,0.9)' }}
          >
            <p
              className="font-mono text-[26px] leading-none font-bold tracking-wider truncate"
              style={{ color: t.lcd, textShadow: `0 0 10px ${t.lcd}` }}
            >
              {lcdMain}
            </p>
            <p className="font-mono text-[10px] mt-1.5 tracking-widest uppercase truncate" style={{ color: t.lcd, opacity: 0.75 }}>
              {lcdSub}
            </p>
          </div>

          {/* Physical buttons */}
          <div className="mt-5 w-full flex items-center justify-between">
            <span
              className="w-11 h-11 rounded-full bg-gradient-to-b from-white to-[#E2E8F0] border border-[#CBD5E1] shadow-[0_3px_0_#B6C0CD] flex items-center justify-center"
              aria-hidden="true"
            >
              <span className="w-2 h-2 rounded-full bg-[#22C55E] shadow-[0_0_6px_#22C55E]" />
            </span>

            <button
              type="button"
              onMouseDown={onMicDown}
              onMouseUp={onMicUp}
              onMouseLeave={onMicUp}
              onTouchStart={(e) => {
                e.preventDefault()
                onMicDown()
              }}
              onTouchEnd={onMicUp}
              className={`h-12 px-5 rounded-full flex items-center gap-2 text-[12px] font-bold uppercase tracking-wide transition-all cursor-pointer ${
                isMicPressed
                  ? 'bg-[#FF5426] text-white translate-y-[2px] shadow-[0_1px_0_#C2360F,0_0_18px_rgba(255,84,38,0.6)]'
                  : 'bg-gradient-to-b from-[#FF6A3D] to-[#F04A1A] text-white shadow-[0_4px_0_#C2360F] hover:brightness-105'
              }`}
            >
              <Mic className="w-4 h-4" />
              {isMicPressed ? 'Listening…' : 'Hold to talk'}
            </button>

            <button
              type="button"
              onClick={onStop}
              disabled={!canStop}
              title="Stop voice"
              aria-label="Stop voice"
              className={`w-11 h-11 rounded-full border flex items-center justify-center transition-all ${
                canStop
                  ? 'bg-gradient-to-b from-white to-[#FEE2E2] border-[#FCA5A5] text-[#DC2626] shadow-[0_3px_0_#F1A1A1] cursor-pointer active:translate-y-[2px]'
                  : 'bg-gradient-to-b from-white to-[#E2E8F0] border-[#CBD5E1] text-[#94A3B8] shadow-[0_3px_0_#B6C0CD] cursor-not-allowed'
              }`}
            >
              <Square className="w-3.5 h-3.5 fill-current" />
            </button>
          </div>
        </div>

        {/* Stand */}
        <div className="w-[200px] h-4 rounded-b-[18px] bg-gradient-to-b from-[#C7CFDA] to-[#AEB8C6]" />
        <div className="w-[240px] h-3 mt-1 rounded-full bg-[#0F172A]/15 blur-[6px]" />
      </div>
    </div>
  )
}
