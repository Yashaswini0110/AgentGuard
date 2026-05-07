import { Shield, ArrowRight } from 'lucide-react'
import { Link } from 'react-router'

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0A0A0F' }}>
      {/* Hero section */}
      <section className="relative flex flex-col" style={{ minHeight: '100vh' }}>
        {/* Top strip */}
        <div
          className="flex items-center justify-between px-8"
          style={{ height: '60px', borderBottom: '1px solid #1A1A2E' }}
        >
          <div className="flex items-center gap-2">
            <Shield size={18} color="#FFFFFF" />
            <span className="font-sans font-semibold text-sm text-white">AgentGuard</span>
            <span className="font-mono text-[11px]" style={{ color: '#6B7280' }}>v3</span>
          </div>
          <Link
            to="/login"
            className="inline-flex items-center gap-1 font-sans text-sm px-4 py-2 rounded-md transition-colors hover:opacity-90"
            style={{ border: '1px solid #FFFFFF', color: '#FFFFFF', textDecoration: 'none' }}
          >
            Demo sign-in <ArrowRight size={14} />
          </Link>
        </div>

        {/* Center content */}
        <div className="flex-1 flex flex-col justify-center px-8" style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
          <p
            className="font-mono text-[11px] uppercase mb-6"
            style={{ color: '#6B7280', letterSpacing: '0.12em' }}
          >
            UNISYS Innovation Challenge 2026
          </p>
          <h1
            className="font-sans font-semibold text-white"
            style={{ fontSize: '44px', lineHeight: '1.15', maxWidth: '560px' }}
          >
            Stop discriminatory AI hiring before it happens.
          </h1>
          <p
            className="font-sans text-base mt-5"
            style={{ color: '#9CA3AF', maxWidth: '520px' }}
          >
            AgentGuard v3 intercepts AI hiring decisions in real time, checks them for bias and regulatory violations, and generates tamper-proof legal evidence of every decision made.
          </p>
          <div className="flex items-center gap-4 mt-9">
            <Link
              to="/login"
              className="inline-flex items-center gap-1 font-sans text-sm font-medium px-6 py-3 rounded-lg transition-opacity hover:opacity-90"
              style={{ backgroundColor: '#0D6EFD', color: '#FFFFFF', textDecoration: 'none' }}
            >
              Sign in (demo) <ArrowRight size={14} />
            </Link>
            <button
              className="inline-flex items-center gap-1 font-sans text-sm px-6 py-3 rounded-lg bg-transparent transition-opacity hover:opacity-80"
              style={{ border: '1px solid #374151', color: '#9CA3AF' }}
            >
              See how it works
            </button>
          </div>
        </div>
      </section>

      {/* Feature strip */}
      <div style={{ backgroundColor: '#FFFFFF' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '64px 24px' }}>
          <div style={{ borderTop: '1px solid #E4E2DC' }} className="pt-16">
            <div className="grid grid-cols-3" style={{ gap: '40px' }}>
              <div>
                <p
                  className="font-mono text-[11px] uppercase mb-3"
                  style={{ color: '#9B9B9B', letterSpacing: '0.1em' }}
                >
                  POLICY ENGINE
                </p>
                <h3 className="font-sans font-semibold text-lg mb-3" style={{ color: '#0D0D0D' }}>
                  Hard blocks before execution
                </h3>
                <p
                  className="font-sans text-sm"
                  style={{ color: '#6B6B6B', lineHeight: '1.7' }}
                >
                  Pure Python rules check every AI decision for prohibited features — institution tier, surname, emotion scores. If a rule fires, the decision is blocked in under 5ms. Zero AI. No exceptions.
                </p>
              </div>
              <div>
                <p
                  className="font-mono text-[11px] uppercase mb-3"
                  style={{ color: '#9B9B9B', letterSpacing: '0.1em' }}
                >
                  RISK ROUTER
                </p>
                <h3 className="font-sans font-semibold text-lg mb-3" style={{ color: '#0D0D0D' }}>
                  Three-tier risk classification
                </h3>
                <p
                  className="font-sans text-sm"
                  style={{ color: '#6B6B6B', lineHeight: '1.7' }}
                >
                  A scikit-learn gradient boost classifier scores every passing decision GREEN, YELLOW, or RED in under 50ms. SHAP values explain exactly which features drove the routing. Supervisor LLM invoked only for borderline cases.
                </p>
              </div>
              <div>
                <p
                  className="font-mono text-[11px] uppercase mb-3"
                  style={{ color: '#9B9B9B', letterSpacing: '0.1em' }}
                >
                  SIGNED ARTIFACTS
                </p>
                <h3 className="font-sans font-semibold text-lg mb-3" style={{ color: '#0D0D0D' }}>
                  Legal-grade audit evidence
                </h3>
                <p
                  className="font-sans text-sm"
                  style={{ color: '#6B6B6B', lineHeight: '1.7' }}
                >
                  Every decision generates a SHA-256 signed JSON artifact. If anyone modifies a single character, the hash mismatch is instantly detectable. Tamper-proof compliance documentation for EU AI Act and DPDP Act.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer
        className="flex items-center justify-between px-6"
        style={{
          backgroundColor: '#0A0A0F',
          padding: '24px',
          borderTop: '1px solid #1A1A2E',
        }}
      >
        <span className="font-mono text-xs" style={{ color: '#6B7280' }}>
          AgentGuard v3.1 — AI Governance Control Plane for Enterprise HR
        </span>
        <span className="font-mono text-xs" style={{ color: '#6B7280' }}>
          Built for UNISYS Innovation Challenge 2026
        </span>
      </footer>
    </div>
  )
}
