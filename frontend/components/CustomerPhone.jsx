'use client'

import React from 'react'
import {
  Signal,
  Wifi,
  BatteryFull,
  ChevronLeft,
  ShieldCheck,
  Volume2,
  Clock,
  CheckCircle2,
  RotateCcw,
  RefreshCw,
  Loader2,
  Lock
} from 'lucide-react'

// Customer's UPI app on a realistic phone: dark bezel, bright light screen.
export default function CustomerPhone({
  paymentStatus,
  activeCase,
  receipt,
  soundboxSpeaking,
  caption,
  onPay,
  onRetap
}) {
  const pending = paymentStatus === 'PENDING'
  const processing = paymentStatus === 'PROCESSING'
  const confirmed = paymentStatus === 'CONFIRMED'
  const refunded = paymentStatus === 'REFUNDED'

  return (
    <div className="relative select-none" style={{ width: 316 }}>
      {/* Side buttons */}
      <span className="absolute -left-[3px] top-[120px] h-8 w-[3px] rounded-l bg-[#2B3240]" />
      <span className="absolute -left-[3px] top-[170px] h-14 w-[3px] rounded-l bg-[#2B3240]" />
      <span className="absolute -left-[3px] top-[236px] h-14 w-[3px] rounded-l bg-[#2B3240]" />
      <span className="absolute -right-[3px] top-[190px] h-20 w-[3px] rounded-r bg-[#2B3240]" />

      {/* Bezel */}
      <div
        className="rounded-[52px] p-[10px]"
        style={{
          background: 'linear-gradient(160deg, #3A4252 0%, #161A22 45%, #0B0E14 100%)',
          boxShadow: '0 30px 60px -20px rgba(15,23,42,0.45), 0 0 0 1px rgba(15,23,42,0.6), inset 0 1px 1px rgba(255,255,255,0.15)'
        }}
      >
        {/* Screen */}
        <div className="relative h-[640px] rounded-[42px] bg-white overflow-hidden flex flex-col">
          {/* Status bar + dynamic island */}
          <div className="relative h-11 px-7 flex items-center justify-between text-[13px] font-semibold text-[#0F172A]">
            <span>12:04</span>
            <span className="absolute left-1/2 top-2.5 -translate-x-1/2 h-[26px] w-[96px] rounded-full bg-black" />
            <span className="flex items-center gap-1">
              <Signal className="w-3.5 h-3.5" />
              <Wifi className="w-3.5 h-3.5" />
              <BatteryFull className="w-5 h-5" />
            </span>
          </div>

          {/* App bar */}
          <div className="px-5 py-2 flex items-center gap-2 border-b border-[#EEF1F5]">
            <ChevronLeft className="w-5 h-5 text-[#334155]" />
            <span className="text-[15px] font-semibold text-[#0F172A]">Pay with UPI</span>
            <span className="ml-auto flex items-center gap-1 text-[11px] font-medium text-[#15803D]">
              <Lock className="w-3 h-3" /> Secure
            </span>
          </div>

          <div className="flex-1 flex flex-col px-5 pt-3 pb-4 bg-gradient-to-b from-white to-[#F6F8FB]">
            {/* Case lock banner: tells this customer the soundbox is talking about their payment */}
            {activeCase && (
              <div
                role="status"
                aria-live="assertive"
                className="rounded-2xl border-2 border-amber-400 bg-amber-50 px-3 py-2.5 text-center shadow-[0_8px_24px_-10px_rgba(245,158,11,0.6)]"
              >
                <p className="text-[11px] font-bold uppercase tracking-widest text-amber-700">
                  Case {activeCase.id} Opened
                </p>
                <p className="text-[26px] font-black text-[#0F172A] leading-tight">Amount: ₹{activeCase.amount ?? 40}</p>
                <p
                  className={`text-[12px] font-medium mt-0.5 flex items-center justify-center gap-1.5 ${
                    soundboxSpeaking ? 'text-amber-700 animate-pulse' : 'text-amber-800/80'
                  }`}
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  {soundboxSpeaking
                    ? 'Soundbox is speaking to you'
                    : activeCase.status === 'AWAITING_APPROVAL'
                    ? 'Refund awaiting merchant approval'
                    : 'Your money is safe · Do not pay again'}
                </p>
              </div>
            )}

            {/* Bharosa Receipt in the customer's language once the case is resolved */}
            {!activeCase && receipt && (
              <div
                role="status"
                className={`rounded-2xl border px-3 py-2.5 text-center ${
                  receipt.outcome === 'refunded' ? 'border-sky-300 bg-sky-50' : 'border-emerald-300 bg-emerald-50'
                }`}
              >
                <p className="text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Bharosa Receipt</p>
                <p className="text-[14px] font-semibold text-[#0F172A] leading-snug mt-1 font-hindi">{receipt.customer?.text}</p>
                <p className="text-[10px] font-mono text-[#94A3B8] mt-1 truncate" title={receipt.audit_hash}>
                  audit {receipt.audit_hash?.slice(0, 16)}…
                </p>
              </div>
            )}

            {/* Merchant + amount */}
            <div className="my-auto flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-full bg-[#FFF1EC] border-4 border-white shadow-md flex items-center justify-center text-3xl">
                ☕
              </div>
              <p className="mt-2 text-[17px] font-bold text-[#0F172A]">Ravi&apos;s Chai Stall</p>
              <p className="text-[12px] text-[#64748B] flex items-center gap-1">
                ravi.chai@upi <ShieldCheck className="w-3.5 h-3.5 text-[#15803D]" />
              </p>

              <p className="mt-4 text-[11px] font-semibold uppercase tracking-widest text-[#94A3B8]">Amount</p>
              <p className="text-[64px] leading-none font-black tracking-tight text-[#0F172A]">
                <span className="text-[34px] align-top mr-1 text-[#475569]">₹</span>40
              </p>

              <div className="h-8 mt-3 flex items-center">
                {pending && (
                  <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-[12px] font-semibold flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 animate-spin" /> Bank pending
                  </span>
                )}
                {confirmed && (
                  <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[12px] font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Payment successful
                  </span>
                )}
                {refunded && (
                  <span className="px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-[12px] font-semibold flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5" /> Refunded · ₹40 returned
                  </span>
                )}
              </div>
            </div>

            {/* Pay button: while pending, a second tap is a retap the server blocks, never a new charge */}
            <button
              type="button"
              onClick={pending ? onRetap : onPay}
              disabled={processing}
              className={`w-full h-14 rounded-2xl text-[17px] font-bold text-white flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer disabled:cursor-wait ${
                processing
                  ? 'bg-[#94A3B8]'
                  : confirmed
                  ? 'bg-[#16A34A] hover:bg-[#15803D] shadow-[0_10px_24px_-10px_rgba(22,163,74,0.8)]'
                  : pending
                  ? 'bg-amber-500 hover:bg-amber-600 shadow-[0_10px_24px_-10px_rgba(245,158,11,0.8)]'
                  : 'bg-[#FF5426] hover:bg-[#E8461B] shadow-[0_10px_24px_-10px_rgba(255,84,38,0.8)]'
              }`}
            >
              {processing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Processing…
                </>
              ) : confirmed ? (
                <>
                  <CheckCircle2 className="w-5 h-5" /> Paid ₹40 · Pay again
                </>
              ) : pending ? (
                <>
                  <RefreshCw className="w-5 h-5" /> Pay Again (Retap)
                </>
              ) : (
                'Pay ₹40'
              )}
            </button>

            {/* Live caption from the soundbox */}
            <div className="mt-3 min-h-[64px] rounded-2xl bg-[#F1F5F9] border border-[#E2E8F0] px-3 py-2 flex items-start gap-2">
              <Volume2 className={`w-4 h-4 mt-0.5 shrink-0 ${soundboxSpeaking ? 'text-[#FF5426]' : 'text-[#94A3B8]'}`} />
              <p className="text-[12px] leading-snug text-[#334155]">{caption}</p>
            </div>
          </div>

          {/* Home indicator */}
          <div className="h-6 flex items-center justify-center bg-[#F6F8FB]">
            <span className="h-[5px] w-28 rounded-full bg-[#0F172A]" />
          </div>
        </div>
      </div>
    </div>
  )
}
