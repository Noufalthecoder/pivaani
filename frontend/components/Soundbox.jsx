'use client'

import React, { useMemo } from 'react'
import { Mic, Square } from 'lucide-react'

// Status-rim / LCD accent per device state
const TONES = {
  idle: { ring: '#F8FAFC', glow: 'rgba(15,23,42,0.12)', lcd: '#7DD3FC' },
  listening: { ring: '#FF5426', glow: 'rgba(255,84,38,0.55)', lcd: '#FDBA74' },
  case: { ring: '#F59E0B', glow: 'rgba(245,158,11,0.6)', lcd: '#FCD34D' },
  speaking: { ring: '#22C55E', glow: 'rgba(34,197,94,0.55)', lcd: '#86EFAC' },
  blocked: { ring: '#EF4444', glow: 'rgba(239,68,68,0.55)', lcd: '#FCA5A5' },
  confirmed: { ring: '#22C55E', glow: 'rgba(34,197,94,0.35)', lcd: '#86EFAC' }
}

// Decorative 25x25 QR-style pattern with the three finder squares
function useQrCells() {
  return useMemo(() => {
    const size = 25
    const corners = [[0, 0], [0, size - 7], [size - 7, 0]]
    const finder = (r, c) => {
      for (const [fr, fc] of corners) {
        const y = r - fr
        const x = c - fc
        if (y >= -1 && y <= 7 && x >= -1 && x <= 7) {
          if (y < 0 || y > 6 || x < 0 || x > 6) return false
          return y === 0 || y === 6 || x === 0 || x === 6 || (y >= 2 && y <= 4 && x >= 2 && x <= 4)
        }
      }
      return null
    }
    const cells = []
    let seed = 11
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        seed = (seed * 1103515245 + 12345) % 2147483648
        const f = finder(r, c)
        cells.push(f === null ? seed % 7 < 3 : f)
      }
    }
    return cells
  }, [])
}

/**
 * Counter QR soundbox: a cube with the Pi Vaani QR standee on its face, speaker
 * grille on the side (sound waves radiate from it while talking), a status rim
 * coloured by state, an LCD strip and physical buttons.
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
  const waveColor = tone === 'idle' ? '#00BAF2' : t.ring

  return (
    <div className="relative flex flex-col items-center select-none">
      <div className="relative w-[330px] h-[330px]">
        {/* Sound waves out of the side speaker */}
        <div className="absolute left-[-6px] top-[150px] w-0 h-0" aria-hidden="true">
          {speaking &&
            [0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className="pv-wave absolute rounded-full"
                style={{
                  width: 90,
                  height: 90,
                  left: -45,
                  top: -45,
                  // Longhands only (no `border` shorthand): just the left arc is visible
                  borderStyle: 'solid',
                  borderWidth: 4,
                  borderTopColor: 'transparent',
                  borderRightColor: 'transparent',
                  borderBottomColor: 'transparent',
                  borderLeftColor: waveColor,
                  animationDelay: `${i * 0.35}s`
                }}
              />
            ))}
          {speaking && (
            <div className="absolute -left-[66px] -top-[16px] flex items-center gap-[3px] h-8">
              {[0, 1, 2, 3, 4].map((i) => (
                <span key={i} className="pv-bar w-[4px] rounded-full" style={{ background: waveColor, animationDelay: `${i * 0.12}s` }} />
              ))}
            </div>
          )}
        </div>

        {/* Side body with speaker grille (perspective) */}
        <div
          className="absolute left-[14px] top-[38px] w-[62px] h-[270px] rounded-l-[30px]"
          style={{
            background: 'linear-gradient(90deg, #1F3F66 0%, #3E6A96 65%, #2C5582 100%)',
            transform: 'skewY(-12deg)',
            boxShadow: 'inset 6px 0 14px rgba(0,0,0,0.35)'
          }}
          aria-hidden="true"
        >
          <div
            className="absolute left-[16px] top-[86px] w-[26px] h-[70px] rounded-md"
            style={{
              backgroundImage: 'radial-gradient(#0B1626 1.6px, transparent 2px)',
              backgroundSize: '7px 7px'
            }}
          />
        </div>

        {/* Front face: status rim + QR standee */}
        <div
          className="absolute right-0 top-0 w-[270px] h-[310px] rounded-[38px] overflow-hidden transition-all duration-300"
          style={{
            border: `7px solid ${t.ring}`,
            boxShadow: `0 0 30px ${t.glow}, 0 30px 50px -24px rgba(15,23,42,0.55)`,
            background: 'linear-gradient(180deg, #00BAF2 0%, #00B2EA 55%, #0B2A78 55%, #082061 100%)'
          }}
        >
          <div
            className={`absolute inset-[14px] rounded-[22px] bg-white flex flex-col items-center px-3 pt-3 pb-2 ${
              tone === 'case' && !speaking ? 'animate-pulse' : ''
            }`}
          >
            <p className="text-[18px] font-extrabold leading-none tracking-tight text-[#0F172A]">
              Pi <span className="text-[#FF5426]">Vaani</span>
            </p>
            <p className="text-[9px] font-semibold text-[#334155] mt-0.5">Accepted Here</p>
            <p className="text-[9px] font-bold text-[#0F172A] mt-1">Scan &amp; Pay using any UPI App</p>
            <div className="relative mt-1.5 grid grid-cols-[repeat(25,1fr)] w-[118px] h-[118px]">
              {qr.map((on, i) => (
                <span key={i} className={on ? 'bg-[#0F172A]' : 'bg-transparent'} />
              ))}
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-md bg-white flex items-center justify-center text-[10px] font-black text-[#FF5426]">
                Pi
              </span>
            </div>
            <p className="text-[8px] text-[#475569] mt-1">UPI ID: ravi.chai@upi</p>

            {/* LCD strip */}
            <div
              className="mt-auto w-full rounded-lg px-2.5 py-1.5"
              style={{ backgroundColor: '#0B1220', boxShadow: 'inset 0 2px 6px rgba(0,0,0,0.8)' }}
            >
              <p className="font-mono text-[16px] leading-none font-bold truncate" style={{ color: t.lcd, textShadow: `0 0 8px ${t.lcd}` }}>
                {lcdMain}
              </p>
              <p className="font-mono text-[8.5px] mt-1 tracking-widest uppercase truncate" style={{ color: t.lcd, opacity: 0.8 }}>
                {lcdSub}
              </p>
            </div>
          </div>
        </div>

        {/* Base shadow */}
        <div className="absolute left-[30px] right-[10px] bottom-[4px] h-4 rounded-full bg-[#0F172A]/20 blur-[8px]" />
      </div>

      {/* Physical buttons */}
      <div className="mt-2 w-[270px] ml-[60px] flex items-center justify-between">
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
          className={`h-11 px-5 rounded-full flex items-center gap-2 text-[12px] font-bold uppercase tracking-wide transition-all cursor-pointer ${
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
  )
}
