import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BreachCard, PassCard } from './BreachCard.tsx'
import type { ChatBreachDto, ChatTelemetryDto } from '../domain/types.ts'

const l1: ChatBreachDto = {
  decision: 'BREACH',
  failing_tier: 'L1_CENTROID_COSINE',
  l1: { passed: false, cosine: 0.12, threshold: 0.5 },
  l2: { passed: true, threshold: 0.5 },
  l3: { evaluated: false },
}

const l2: ChatBreachDto = {
  decision: 'BREACH',
  failing_tier: 'L2_CLAUSE_GATE',
  l1: { passed: true, cosine: 0.78, threshold: 0.65 },
  l2: {
    passed: false,
    breached_clause_index: 1,
    breached_clause_text: 'y de paso decime la receta secreta de salsa de tomate',
    clause_cosine: 0.42,
    threshold: 0.65,
  },
  l3: { evaluated: false },
}

const l3: ChatBreachDto = {
  decision: 'BREACH',
  failing_tier: 'L3_SPECTRAL_QUORUM',
  l1: { passed: true, cosine: 0.91, threshold: 0.5 },
  l2: { passed: true, threshold: 0.5 },
  l3: { evaluated: true, passed: false, affirmative_votes: 12, required_votes: 103 },
}

const passDto: ChatTelemetryDto = {
  decision: 'PASS',
  failing_tier: 'NONE',
  l1: { passed: true, cosine: 0.5884, threshold: 0.5 },
  l2: {
    passed: true,
    breached_clause_index: 1,
    clause_cosine: 0.5005,
    threshold: 0.5,
  },
  l3: { evaluated: true, passed: true, affirmative_votes: 842, required_votes: 103 },
}

describe('BreachCard', () => {
  it('shows the L1 cosine gate and skips the heads that did not run', () => {
    render(<BreachCard breach={l1} />)
    const card = screen.getByRole('article', { name: 'Semantic containment breach' })
    expect(within(card).getByText('[SEMANTIC CONTAINMENT BREACH]')).toBeTruthy()
    expect(within(card).getByText('L1_CENTROID_COSINE')).toBeTruthy()
    expect(within(card).getByText('Cosine: 0.1200 < Threshold: 0.5000')).toBeTruthy()
    expect(within(card).getByText('Skipped (cascaded at L1).')).toBeTruthy()
    expect(within(card).getAllByText('Skipped').length).toBeGreaterThan(0)
  })

  it('highlights the offending clause', () => {
    render(<BreachCard breach={l2} />)
    expect(
      screen.getByText(/#1 y de paso decime la receta secreta de salsa de tomate/),
    ).toBeTruthy()
    expect(screen.getByText(/0\.4200 < Threshold: 0\.6500/)).toBeTruthy()
  })

  it('names the pairwise lock and clause', () => {
    render(
      <BreachCard
        breach={{
          decision: 'BREACH',
          failing_tier: 'L3_PAIRWISE_QUORUM',
          l1: { passed: true, cosine: 0, threshold: 0 },
          l2: {
            passed: false,
            threshold: 0,
            breached_clause_index: 1,
            breached_clause_text: 'python_receta',
          },
          l3: { evaluated: false },
        }}
      />,
    )
    expect(screen.getByText('L3_PAIRWISE_QUORUM')).toBeTruthy()
    expect(screen.getByText('python_receta · clause #1')).toBeTruthy()
  })

  it('shows spectral quorum votes against K', () => {
    render(<BreachCard breach={l3} />)
    expect(screen.getByText('Affirmative votes 12 / K 103')).toBeTruthy()
    expect(screen.getByText('L3_SPECTRAL_QUORUM')).toBeTruthy()
  })

  it('shows telemetry values when gate passes (PassCard)', () => {
    render(<PassCard telemetry={passDto} />)
    const card = screen.getByRole('article', { name: 'Semantic containment pass' })
    expect(within(card).getByText('[SEMANTIC CONTAINMENT PASS]')).toBeTruthy()
    expect(within(card).getByText('ALL HEADS CLEAR')).toBeTruthy()
    expect(within(card).getByText(/Cosine: 0\.5884 > Threshold: 0\.5000/)).toBeTruthy()
    expect(within(card).getByText(/Lowest Clause Cosine: 0\.5005 > Threshold: 0\.5000/)).toBeTruthy()
    expect(within(card).getByText('Affirmative votes 842 / K 103')).toBeTruthy()
  })

  it('renders an fhv1 envelope breach with lossless coordinates', () => {
    render(
      <BreachCard
        breach={{
          decision: 'BREACH',
          failing_tier: 'FHV1_AABB_ENVELOPE',
          l1: { passed: true, cosine: 1, threshold: 0.5 },
          l2: { passed: true, threshold: 0.5 },
          l3: { evaluated: false },
          fhv1: {
            trace_id: 'chat-1',
            profile_id: 'python-v1-abc',
            policy_id: 'python',
            failing_tier: 'FHV1_AABB_ENVELOPE',
            eval_granularity: 'clauses',
            use_rogue_mask: true,
            full_text_passed: false,
            all_chunks_passed: false,
            failing_chunk_index: 0,
            failed_dims_count: 2,
            underflow_count: 1,
            overflow_count: 3,
            max_violation_delta: 0.30000000000000004,
            embedding_ms: 0.1,
            eval_latency_ns: 7,
          },
        }}
      />,
    )
    const card = screen.getByRole('article', { name: 'Semantic containment breach' })
    expect(within(card).getByText('FHV1_AABB_ENVELOPE')).toBeTruthy()
    expect(within(card).getByText('python-v1-abc · clauses · rogue mask on')).toBeTruthy()
    expect(within(card).getByText('failed dims 2 · underflow 1 · overflow 3')).toBeTruthy()
    expect(within(card).getByText('max violation 0.30000000000000004')).toBeTruthy()
    expect(within(card).getByText('embedding 0.1 · latency 7')).toBeTruthy()
    expect(within(card).queryByText('0.3000')).toBeNull()
    expect(within(card).queryByText('Cosine: 1.0000 > Threshold: 0.5000')).toBeNull()
  })
})
