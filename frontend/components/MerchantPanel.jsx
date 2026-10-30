'use client'

import React from 'react'
import { ShieldCheck, ShieldAlert, Clock, CheckCircle2, XCircle } from 'lucide-react'

const GATE_DEFINITIONS = [
  { name: 'Authority', desc: 'Signer verification & channel origin' },
  { name: 'Amount', desc: 'Threshold check within merchant bounds' },
  { name: 'Confidence', desc: 'Banking gateway telemetry score >= 0.85' },
  { name: 'Identity', desc: 'Fraud graph & biometric identity check' },
  { name: 'Idempotency', desc: 'Zero in-flight collisions (< 10ms lock)' },
  { name: 'Reversibility', desc: 'Escrow settlement buffer window' },
  { name: 'Approval', desc: 'Voice PIN authorization gate' }
]

export default function MerchantPanel({
  activeCase,
  gateResults = {},
  isEvaluating = false,
  blockedBy = null
}) {
  return (
    <div
      className="flex-1 rounded-xl p-4 border flex flex-col transition-all"
      style={{
        backgroundColor: '#0A0B0F',
        borderColor: '#23262F'
      }}
    >
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#23262F]">
        <span className="text-xs font-mono text-[#8E95A5] uppercase tracking-wider flex items-center gap-1.5">
          {blockedBy ? (
            <ShieldAlert className="w-3.5 h-3.5 text-[#EF4444]" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5 text-[#22C55E]" />
          )}
          7-Gate Evaluation Panel
        </span>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold ${
            isEvaluating
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
              : blockedBy
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : Object.keys(gateResults).length > 0
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'text-[#8E95A5]'
          }`}
        >
          {isEvaluating
            ? 'EVALUATING'
            : blockedBy
            ? `BLOCKED: ${blockedBy}`
            : Object.keys(gateResults).length > 0
            ? 'ALL GATES PASSED'
            : activeCase
            ? 'CASE ACTIVE'
            : 'ALL IDLE'}
        </span>
      </div>

      <div className="space-y-2.5 flex-1 flex flex-col justify-around">
        {GATE_DEFINITIONS.map((gate, index) => {
          const evalData = gateResults[gate.name]
          const isPassed = evalData && (evalData.status === 'PASSED' || evalData.status === 'AUTO_APPROVED')
          const isFailed = evalData && (evalData.status === 'FAILED' || evalData.status === 'FLAGGED')
          const isEvaluatingGate = isEvaluating && !evalData

          return (
            <div
              key={gate.name}
              className={`flex items-center justify-between py-2 px-3 rounded-lg border transition-all duration-300 ${
                isPassed
                  ? 'border-emerald-500/40 bg-emerald-950/15'
                  : isFailed
                  ? 'border-red-500/50 bg-red-950/20 shadow-[0_0_12px_rgba(239,68,68,0.2)]'
                  : isEvaluatingGate
                  ? 'border-amber-500/30 bg-amber-950/10'
                  : 'hover:border-[#3A3F4D]'
              }`}
              style={{
                backgroundColor: isPassed ? 'rgba(6, 78, 59, 0.15)' : isFailed ? 'rgba(69, 10, 10, 0.25)' : '#14161C',
                borderColor: isPassed ? '#10B981' : isFailed ? '#EF4444' : '#23262F'
              }}
            >
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-mono text-[#8E95A5] w-3.5">
                  0{index + 1}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-medium text-white leading-tight">{gate.name}</p>
                    {isPassed && (
                      <span className="text-[9px] font-mono text-emerald-400 font-semibold px-1.5 py-0.2 rounded bg-emerald-500/20">
                        PASS
                      </span>
                    )}
                    {isFailed && (
                      <span className="text-[9px] font-mono text-red-400 font-semibold px-1.5 py-0.2 rounded bg-red-500/20">
                        FAIL
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] font-mono text-[#8E95A5] leading-none mt-0.5">
                    {evalData?.reason || gate.desc}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span
                  className={`w-3.5 h-3.5 rounded-full border transition-all duration-300 flex items-center justify-center ${
                    isPassed
                      ? 'bg-[#22C55E] border-[#22C55E] shadow-[0_0_10px_#22C55E]'
                      : isFailed
                      ? 'bg-[#EF4444] border-[#EF4444] shadow-[0_0_10px_#EF4444] animate-bounce'
                      : isEvaluatingGate
                      ? 'bg-amber-400 border-amber-400 shadow-[0_0_8px_#f59e0b] animate-ping'
                      : 'bg-[#2A2E39] border-[#3A3F4D]'
                  }`}
                  title={isPassed ? 'Passed' : isFailed ? 'Failed' : isEvaluatingGate ? 'Evaluating' : 'Idle'}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
