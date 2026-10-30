'use client'

import React, { useEffect, useState } from 'react'
import { ShieldCheck, ShieldAlert, Clock, CheckCircle2, XCircle } from 'lucide-react'

const GATE_STEP_MS = 280
const NO_RESULTS = {}

const GATE_DEFINITIONS = [
  { name: 'Authority', desc: 'Only system or merchant channels; approvals need the PIN' },
  { name: 'Amount', desc: '≤ original payment, ≤ ₹5,000 ceiling, auto within dial' },
  { name: 'Confidence', desc: 'Recommender confidence ≥ dial minimum' },
  { name: 'Identity', desc: 'Fraud-ring graph: flagged payers go to review' },
  { name: 'Idempotency', desc: 'No duplicate payments, single-use approval nonces' },
  { name: 'Reversibility', desc: 'Refund only after the bank says it will not settle' },
  { name: 'Approval', desc: 'Merchant voice + PIN when the dial requires it' }
]

// Statuses that hold an action (for the bank or a person) rather than pass or fail it
const HOLD_STATUSES = ['PENDING_APPROVAL', 'REVIEW', 'WAIT']
const HOLD_BADGES = { PENDING_APPROVAL: 'WAIT', REVIEW: 'REVIEW', WAIT: 'BANK' }

export default function MerchantPanel({
  activeCase,
  gateResults = NO_RESULTS,
  decision = null,
  isEvaluating = false,
  blockedBy = null
}) {
  const totalGates = GATE_DEFINITIONS.length
  const hasResults = Object.keys(gateResults).length > 0

  // Reveal each new evaluation gate-by-gate, top to bottom
  const [revealed, setRevealed] = useState(totalGates)
  useEffect(() => {
    if (!hasResults) {
      setRevealed(totalGates)
      return
    }
    setRevealed(0)
    const timers = GATE_DEFINITIONS.map((_, i) => setTimeout(() => setRevealed(i + 1), (i + 1) * GATE_STEP_MS))
    return () => timers.forEach(clearTimeout)
  }, [gateResults, hasResults, totalGates])

  const sweeping = hasResults && revealed < totalGates
  const awaitingApproval = hasResults && decision === 'NEEDS_APPROVAL'
  const holdingForBank = hasResults && decision === 'HOLD'
  const showBlocked = Boolean(blockedBy) && !sweeping

  // Row colours per gate state (light theme)
  const rowStyle = (isPassed, isFailed, isWaiting, isEvaluatingGate) =>
    isPassed
      ? 'border-emerald-200 bg-emerald-50'
      : isFailed
      ? 'border-red-300 bg-red-50 shadow-[0_6px_18px_-10px_rgba(239,68,68,0.7)]'
      : isWaiting || isEvaluatingGate
      ? 'border-amber-300 bg-amber-50'
      : 'border-[#E4E8EF] bg-white'

  return (
    <div className="flex-1 rounded-2xl p-4 border border-[#E4E8EF] bg-[#F8FAFC] flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#64748B] flex items-center gap-1.5">
          {showBlocked ? (
            <ShieldAlert className="w-3.5 h-3.5 text-red-600" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          )}
          7-gate firewall
        </span>
        <span
          className={`text-[10px] px-2 py-1 rounded-lg uppercase tracking-wide font-bold ${
            isEvaluating || sweeping
              ? 'bg-amber-100 text-amber-800 animate-pulse'
              : showBlocked
              ? 'bg-red-600 text-white'
              : awaitingApproval || holdingForBank
              ? 'bg-amber-100 text-amber-800'
              : hasResults
              ? 'bg-emerald-600 text-white'
              : 'bg-white text-[#94A3B8] border border-[#E4E8EF]'
          }`}
        >
          {isEvaluating || sweeping
            ? `Evaluating ${Math.min(revealed + 1, totalGates)}/${totalGates}`
            : showBlocked
            ? `Blocked: ${blockedBy}`
            : awaitingApproval
            ? 'Awaiting approval'
            : holdingForBank
            ? 'Hold: waiting for bank'
            : hasResults
            ? 'All gates passed'
            : activeCase
            ? 'Case active'
            : 'Idle'}
        </span>
      </div>

      <div className="flex-1 flex flex-col gap-2">
        {GATE_DEFINITIONS.map((gate, index) => {
          const evalData = index < revealed ? gateResults[gate.name] : undefined
          const isPassed = evalData && (evalData.status === 'PASSED' || evalData.status === 'AUTO_APPROVED')
          const isFailed = evalData && (evalData.status === 'FAILED' || evalData.status === 'FLAGGED')
          const isWaiting = evalData && HOLD_STATUSES.includes(evalData.status)
          const isEvaluatingGate = (isEvaluating && !evalData) || (sweeping && index === revealed)

          return (
            <div
              key={gate.name}
              className={`flex items-center justify-between py-2 px-3 rounded-xl border transition-all duration-300 ${rowStyle(
                isPassed,
                isFailed,
                isWaiting,
                isEvaluatingGate
              )}`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="text-[10px] font-mono font-bold text-[#94A3B8] w-4 shrink-0">0{index + 1}</span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-semibold text-[#0F172A] leading-tight">{gate.name}</p>
                    {isPassed && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-600 text-white">PASS</span>
                    )}
                    {isFailed && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-600 text-white">FAIL</span>
                    )}
                    {isWaiting && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500 text-white">
                        {HOLD_BADGES[evalData.status]}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#64748B] leading-tight mt-0.5 truncate" title={evalData?.reason || gate.desc}>
                    {isEvaluatingGate ? 'Checking…' : evalData?.reason || gate.desc}
                  </p>
                </div>
              </div>

              <span
                className={`ml-2 shrink-0 w-3.5 h-3.5 rounded-full transition-all duration-300 ${
                  isPassed
                    ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]'
                    : isFailed
                    ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-bounce'
                    : isEvaluatingGate
                    ? 'bg-amber-400 animate-ping'
                    : isWaiting
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-[#E2E8F0]'
                }`}
                title={
                  isPassed ? 'Passed' : isFailed ? 'Failed' : isEvaluatingGate ? 'Evaluating' : isWaiting ? 'On hold' : 'Idle'
                }
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
