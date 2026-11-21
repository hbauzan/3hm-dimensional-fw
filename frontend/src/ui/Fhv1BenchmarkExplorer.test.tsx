import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { memorySessionStore } from '../domain/session.ts'
import { Fhv1BenchmarkExplorer } from './Fhv1BenchmarkExplorer.tsx'

vi.mock('echarts/core', () => ({
  use: () => undefined,
  init: () => ({
    setOption: () => undefined,
    resize: () => undefined,
    dispose: () => undefined,
  }),
}))

vi.mock('echarts/charts', () => ({
  LineChart: {},
  BarChart: {},
  ScatterChart: {},
}))

vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  DataZoomComponent: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

const run = {
  run_id: 'bench-1',
  profile_id: 'python-v1-abc',
  policy_id: 'python',
  dataset_name: 'python',
  eval_granularity: 'full_mirror',
  use_rogue_mask: false,
  total_inputs: 4,
  total_chunks: 4,
}

const detail = {
  ...run,
  summary_metrics: {
    confusion: {
      tp: 1,
      tn: 2,
      fp: 0,
      fn: 1,
      accuracy: 0.75,
      precision: null,
      recall: 0.5,
      f1: null,
      far_fpr: 0,
      frr_fnr: 0.5,
    },
    per_category: {
      IN_DOMAIN_VALID: { tp: 0, tn: 0, fp: 0, fn: 1, far_fpr: null, frr_fnr: 1 },
      OUT_OF_DOMAIN_BENIGN: { tp: 0, tn: 1, fp: 0, fn: 0, far_fpr: 0, frr_fnr: null },
      HYBRID_BOUNDARY: { tp: 0, tn: 1, fp: 0, fn: 0, far_fpr: 0, frr_fnr: null },
      ADVERSARIAL_FUZZING: { tp: 1, tn: 0, fp: 0, fn: 0, far_fpr: null, frr_fnr: 0 },
    },
    attribution: { in_domain_fail_counts: [0, 2, 0, 0] },
  },
}

const drill = {
  trace_id: 'trace-1',
  profile_id: 'python-v1-abc',
  chunks: [
    {
      chunk_index: 0,
      chunk_strategy: 'full_doc',
      chunk_text: 'hola',
      chunk_passed: false,
      dimensions: [
        {
          observed: 0.1,
          observed_bits_hex: '0x3fb999999999999a',
          min: 0,
          max: 0.05,
          status: 'overflow',
          violation_delta: 0.05,
        },
        {
          observed: 0.2,
          observed_bits_hex: '0x3fc999999999999a',
          min: 0,
          max: 1,
          status: 'in_bounds',
          violation_delta: 0,
        },
      ],
    },
  ],
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

function traceRow(traceId: string) {
  return {
    trace_id: traceId,
    source_kind: 'BENCHMARK',
    profile_id: 'python-v1-abc',
    category: 'IN_DOMAIN_VALID',
    chunk_index: 0,
    overall_passed: false,
    failed_dims_count: 1,
    max_violation_delta: 0.1,
  }
}

describe('Fhv1BenchmarkExplorer', () => {
  it('shows the four quadrants, a lossless drill-down, and the next page', async () => {
    const user = userEvent.setup()
    const calls: string[] = []
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      calls.push(url)
      if (url.includes('/api/v1/fhv1/traces/')) return jsonResponse(drill)
      if (url.includes('/api/v1/fhv1/traces?')) {
        const page = Number(new URL(url).searchParams.get('page') ?? '1')
        return jsonResponse({
          page,
          page_size: 20,
          total: 21,
          rows: [traceRow(page === 1 ? 'trace-1' : 'trace-2')],
        })
      }
      if (url.includes('/api/v1/fhv1/benchmarks/')) return jsonResponse(detail)
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([run])
      return new Response(JSON.stringify({ error: url }), { status: 404 })
    }
    function Harness() {
      const [traceId, setTraceId] = useState<string | null>('trace-1')
      return (
        <Fhv1BenchmarkExplorer
          fetchImpl={fetchImpl}
          store={memorySessionStore()}
          traceId={traceId}
          onTraceId={setTraceId}
        />
      )
    }
    render(<Harness />)

    expect(await screen.findByRole('article', { name: 'True positive' })).toBeTruthy()
    expect(screen.getByRole('article', { name: 'IN_DOMAIN_VALID' }).textContent).toContain('frr 1')
    expect(screen.getByRole('img', { name: 'fhv1 attribution' })).toBeTruthy()
    expect(await screen.findByText(/0x3fb999999999999a/)).toBeTruthy()
    expect(screen.getByText(/dim 0 overflow 0\.1 /)).toBeTruthy()
    expect(screen.queryByText('0.1000')).toBeNull()
    expect(screen.queryByText(/0x3fc999999999999a/)).toBeNull()

    await user.click(screen.getByRole('checkbox', { name: 'Show all dimensions' }))
    expect(await screen.findByText(/0x3fc999999999999a/)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(await screen.findByRole('button', { name: 'trace-2' })).toBeTruthy()
    expect(calls.some((url) => url.includes('page=2'))).toBe(true)
  })
})
