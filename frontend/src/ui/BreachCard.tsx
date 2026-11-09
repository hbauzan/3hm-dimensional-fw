import { clampUnit, formatGate } from '../domain/format.ts'
import type { ChatBreachDto, ChatTelemetryDto, Tier1Breach, Tier3Breach } from '../domain/types.ts'

export function BreachCard({ breach }: { breach: ChatBreachDto }) {
  return (
    <article
      aria-label="Semantic containment breach"
      className="border border-studio-warn bg-studio-card px-3 py-3 text-xs"
    >
      <p className="text-[11px] tracking-wide text-studio-warn">[SEMANTIC CONTAINMENT BREACH]</p>
      <p className="mt-1 font-semibold text-studio-breach">{breach.failing_tier}</p>
      <Tier1 tier={breach.l1} />
      <Tier2 telemetry={breach} />
      <Tier3 tier={breach.l3} />
      <DisaggregatedLatency telemetry={breach} />
    </article>
  )
}

export function PassCard({ telemetry }: { telemetry: ChatTelemetryDto }) {
  return (
    <article
      aria-label="Semantic containment pass"
      className="mb-2 border border-studio-pass/50 bg-studio-card px-3 py-3 text-xs"
    >
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold tracking-wide text-studio-pass">[SEMANTIC CONTAINMENT PASS]</p>
        <span className="text-[10px] text-studio-pass font-mono border border-studio-pass/40 bg-studio-pass/10 px-1.5 py-0.5 rounded">
          ALL HEADS CLEAR
        </span>
      </div>
      <Tier1 tier={telemetry.l1} />
      <Tier2 telemetry={telemetry} />
      <Tier3 tier={telemetry.l3} />
      <DisaggregatedLatency telemetry={telemetry} />
    </article>
  )
}

function Tier1({ tier }: { tier: Tier1Breach }) {
  const width = `${clampUnit(tier.cosine) * 100}%`
  const mark = `${clampUnit(tier.threshold) * 100}%`
  return (
    <section aria-label="Tier 1 centroid cosine" className="mt-3">
      <h3 className="text-studio-muted">Tier 1 — Centroid Cosine</h3>
      <p>Cosine: {formatGate(tier.cosine, tier.threshold)}</p>
      <StatusPill passed={tier.passed} />
      <div
        role="img"
        aria-label="centroid cosine proximity"
        className="relative mt-1 h-2 border border-studio-line bg-studio-bg"
      >
        <div
          className={tier.passed ? 'h-full bg-studio-pass' : 'h-full bg-studio-breach'}
          style={{ width }}
        />
        <div className="absolute top-0 h-full w-px bg-studio-accent" style={{ left: mark }} />
      </div>
    </section>
  )
}

function Tier2({ telemetry }: { telemetry: ChatTelemetryDto }) {
  const tier = telemetry.l2
  return (
    <section aria-label="Tier 2 clause gate" className="mt-3">
      <h3 className="text-studio-muted">Tier 2 — Clause Gate</h3>
      {telemetry.failing_tier === 'L3_PAIRWISE_QUORUM' ? (
        <p className="text-studio-breach">
          {tier.breached_clause_text ?? 'pairwise lock'}
          {tier.breached_clause_index === undefined
            ? ' · full prompt'
            : ` · clause #${tier.breached_clause_index}`}
        </p>
      ) : telemetry.failing_tier === 'L1_CENTROID_COSINE' ? (
        <p>Skipped (cascaded at L1).</p>
      ) : tier.passed ? (
        <>
          <StatusPill passed />
          <p>
            {tier.clause_cosine !== undefined
              ? `Lowest Clause Cosine: ${formatGate(tier.clause_cosine, tier.threshold)}${tier.breached_clause_index !== undefined ? ` (Clause #${tier.breached_clause_index})` : ''}`
              : `Threshold: ${tier.threshold.toFixed(4)}`}
          </p>
        </>
      ) : (
        <>
          <StatusPill passed={false} />
          <p className="text-studio-breach">
            #{tier.breached_clause_index ?? '?'} {tier.breached_clause_text ?? ''}
            {tier.clause_cosine === undefined
              ? ''
              : ` — Cosine: ${formatGate(tier.clause_cosine, tier.threshold)}`}
          </p>
        </>
      )}
    </section>
  )
}

function Tier3({ tier }: { tier: Tier3Breach }) {
  return (
    <section aria-label="Tier 3 Subspace Coordinate Quorum (K-of-D L∞ Gate)" className="mt-3">
      <h3 className="text-studio-muted">Tier 3 — Subspace Coordinate Quorum (K-of-D L∞ Gate)</h3>
      {tier.evaluated &&
      tier.affirmative_votes !== undefined &&
      tier.required_votes !== undefined ? (
        <>
          <p>
            Affirmative votes {tier.affirmative_votes} / K {tier.required_votes}
          </p>
          {typeof tier.passed === 'boolean' ? <StatusPill passed={tier.passed} /> : null}
        </>
      ) : (
        <p>Skipped</p>
      )}
    </section>
  )
}

function DisaggregatedLatency({ telemetry }: { telemetry: ChatTelemetryDto }) {
  const hasLatency =
    telemetry.normalizer_segmenter_us !== undefined ||
    telemetry.simd_gate_kernel_us !== undefined ||
    telemetry.embedding_inference_ms !== undefined
  const hasSkipped = telemetry.clauses_skipped !== undefined && telemetry.clauses_skipped > 0
  if (!hasLatency && !hasSkipped) return null
  return (
    <div className="mt-3 pt-2 border-t border-studio-line text-[10px] text-studio-muted font-mono">
      {hasSkipped && (
        <p className="text-studio-warn font-semibold">
          Sequential Early-Exit: {telemetry.clauses_skipped} downstream clauses skipped
        </p>
      )}
      {hasLatency && (
        <div className="grid grid-cols-2 gap-1 mt-1 text-[10px]">
          <span>Norm/Segment: {telemetry.normalizer_segmenter_us ?? 0} µs</span>
          <span>Embed: {telemetry.embedding_inference_ms !== undefined ? `${telemetry.embedding_inference_ms.toFixed(2)} ms` : '0.00 ms'}</span>
          <span>SIMD Gate: {telemetry.simd_gate_kernel_us ?? 0} µs</span>
          <span>Total: {telemetry.total_pipeline_ms !== undefined ? `${telemetry.total_pipeline_ms.toFixed(2)} ms` : '0.00 ms'}</span>
        </div>
      )}
    </div>
  )
}

function StatusPill({ passed }: { passed: boolean }) {
  return (
    <p className={passed ? 'text-studio-pass' : 'text-studio-breach'}>
      {passed ? '[PASS]' : '[BREACH]'}
    </p>
  )
}
