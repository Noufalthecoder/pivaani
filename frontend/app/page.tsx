'use client'

import Link from 'next/link'
import { useEffect } from 'react'

const gates = ['Authority', 'Amount', 'Confidence', 'Identity', 'Idempotency', 'Reversibility', 'Approval']

function FadeSection({ children, className = '', id, labelledBy }: { children: React.ReactNode; className?: string; id?: string; labelledBy?: string }) {
  return <section id={id} aria-labelledby={labelledBy} className={`fade-section ${className}`}>{children}</section>
}

function SectionIntro({ eyebrow, title, id, children }: { eyebrow: string; title: string; id: string; children?: React.ReactNode }) {
  return <div className="section-intro"><p className="eyebrow">{eyebrow}</p><h2 id={id}>{title}</h2>{children}</div>
}

function HeroVisual() {
  return <div className="hero-visual" aria-label="Pi Vaani UPI Soundbox with payment safety status">
    <div className="soundbox-stage">
      <div className="floating-panel floating-panel-top"><span>Case PV-1001</span><strong>Payment stuck &gt; 2s.</strong></div>
      <div className="floating-panel floating-panel-bottom"><span>Duplicate Blocked</span><strong>Idempotency Gate.</strong></div>
      <div className="soundbox-wrap">
        <div className="soundbox">
          <div className="soundbox-face">
            <div className="led" aria-label="Soundbox listening" />
            <p className="soundbox-brand">Pi Vaani</p>
            <p className="soundbox-subtitle">Accepted Here</p>
            <div className="speaker speaker-left" aria-hidden="true" />
            <div className="speaker speaker-right" aria-hidden="true" />
            <div className="qr-code" aria-label="Sample payment QR code"><span /></div>
            <div className="upi-badge">UPI</div>
          </div>
        </div>
      </div>
    </div>
  </div>
}

export default function Page() {
  useEffect(() => {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => entry.isIntersecting && entry.target.classList.add('is-visible')), { threshold: 0.12 })
    document.querySelectorAll('.fade-section').forEach(section => observer.observe(section))
    return () => observer.disconnect()
  }, [])

  return <main>
    <header className="topbar container"><Link href="/" className="brand">Pi Vaani <span aria-hidden="true">●</span></Link><div className="topbar-right"><span className="mono muted">BHAROSA LAYER</span><Link className="button button-small" href="/demo">Enter Demo →</Link></div></header>

    <FadeSection className="hero container"><div className="hero-copy"><p className="eyebrow">BHAROSA LAYER · FOR UPI</p><h1>No customer pays twice.<br />No merchant loses a sale.</h1><p className="lead">Pi Vaani resolves stuck UPI payments in 2 seconds — in the customer&apos;s language, inside rules the merchant set by voice.</p><p className="micro italic">For the ₹40 that matters at Ravi&apos;s chai stall.</p><div className="cta-row"><Link className="button" href="/demo">Enter Demo →</Link><a className="button button-ghost" href="#how-it-works">See how it works</a></div><p className="trust-strip mono">Deterministic firewall <span>·</span> Voice in <span className="font-hindi">हिंदी</span> / <span className="font-tamil">தமிழ்</span> <span>·</span> Mock sandbox</p></div><HeroVisual /></FadeSection>

    <FadeSection className="problem container"><div className="stat"><strong>15B+</strong><span>UPI transactions every month</span></div><div className="stat"><strong>Every stuck payment</strong><span>is a support call, a churn risk, a trust hit</span></div><div className="stat"><strong>0 humans</strong><span>needed to resolve it — if the layer is right</span></div></FadeSection>

    <FadeSection id="how-it-works" labelledBy="how-title" className="section container"><SectionIntro eyebrow="HOW IT WORKS" title="Three steps. Two seconds. No humans." id="how-title" /><div className="card-grid">{[['01', 'Payment gets stuck.', 'Within 2 seconds, a case opens automatically. No human notices the problem — because no human needs to.'], ['02', 'The Soundbox speaks.', 'The customer hears it in Hindi. The merchant hears it in Tamil. Both hear the same truth at the same time.'], ['03', 'Seven gates decide.', 'The LLM recommends. Deterministic Python decides. Every decision is logged to a hash chain that cannot be quietly edited.']].map(([num, title, body]) => <article className="card" key={num}><p className="card-number mono">{num}</p><h3>{title}</h3><p>{body}</p></article>)}</div></FadeSection>

    <FadeSection labelledBy="dial-title" className="section container"><SectionIntro eyebrow="THE TRUST DIAL" title="The merchant sets the rules. By voice." id="dial-title"><p className="section-subhead">One line — &quot;Careful rakho&quot; — and the whole layer changes how it acts. No forms. No settings page. No English required.</p></SectionIntro><div className="card-grid">{[['Careful', 'Voice approval and PIN required.', 'auto_refund_max ₹0', 'min_confidence 0.90'], ['Balanced', 'Voice approval required.', 'auto_refund_max ₹200', 'min_confidence 0.80'], ['Fast', 'Auto-refunds, no prompt.', 'auto_refund_max ₹500', 'min_confidence 0.70']].map(([title, outcome, config, confidence]) => <article className="card dial-card" key={title}><h3>{title}</h3><p>{outcome}</p><p className="mono config">— {config}<br />— {confidence}</p></article>)}</div><p className="under-caption">Outcome for a ₹500 refund at 0.92 confidence.</p></FadeSection>

    <FadeSection labelledBy="firewall-title" className="section container"><SectionIntro eyebrow="THE FIREWALL" title="A fooled AI is still safe here." id="firewall-title"><p className="section-subhead">The LLM never executes. Every money action passes seven deterministic gates — no exceptions, no shortcuts, no &quot;just this once.&quot;</p></SectionIntro><div className="gate-chips">{gates.map(gate => <span className="gate-chip" key={gate}><i aria-hidden="true" />{gate}</span>)}</div><p className="mono firewall-line">&gt; Try to break it in the demo. Six attacks are preloaded.</p></FadeSection>

    <FadeSection className="final-cta"><div className="container"><h2>See Pi Vaani resolve a real stuck payment in 30 seconds.</h2><Link className="button button-large" href="/demo">Enter Demo →</Link><p className="micro">Soundbox emulator · mock payment sandbox · no real money moves</p></div></FadeSection>
    <footer className="footer container"><span>Pi Vaani · Team ImpactMinds</span><span className="mono">Soundbox emulator · mock payment sandbox</span></footer>
  </main>
}
