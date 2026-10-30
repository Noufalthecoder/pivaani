'use client'

import dynamic from 'next/dynamic'

const Demo = dynamic(() => import('@/Demo'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-[#F3F5F9] flex items-center justify-center text-slate-500 font-mono text-sm">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        Loading Pi Vaani Sandbox Dashboard...
      </div>
    </div>
  ),
})

export default function DemoPage() {
  return <Demo />
}
