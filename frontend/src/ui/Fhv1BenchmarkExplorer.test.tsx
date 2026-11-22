import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { memorySessionStore } from '../domain/session.ts'
import { listFhv1Traces } from '../gateway/fhv1Client.ts'
import { Fhv1BenchmarkExplorer } from './Fhv1BenchmarkExplorer.tsx'
import { attributionOption, drilldownVectorOption, failedDimsHistogramOption } from './fhv1Charts.ts'

const charts = vi.hoisted(() => ({
  options: [] as {
    xAxis?: { data?: unknown[] }
    series?: { name?: string; type?: string; data?: unknown[]; itemStyle?: { color?: string } }[]
    tooltip?: { formatter?: (params: unknown) => string }
  }[],
}))

vi.mock('echarts/core', () => ({
  use: () => undefined,
  init: () => ({
    setOption: (option: (typeof charts.options)[number]) => {
      charts.options.push(option)
    },
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
          mean: 0.025,
          status: 'overflow',
          violation_delta: 0.05,
          delta_vs_mean: 0.07500000000000001,
          norm_pos: 2,
        },
        {
          observed: 0.2,
          observed_bits_hex: '0x3fc999999999999a',
          min: 0,
          max: 1,
          mean: 0.5,
          status: 'in_bounds',
          violation_delta: 0,
          delta_vs_mean: -0.3,
          norm_pos: 0.2,
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
  beforeEach(() => {
    charts.options.length = 0
  })

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
    expect(screen.getByText(/mean 0\.025/)).toBeTruthy()
    expect(screen.getByText(/overflow x-max=0\.05/)).toBeTruthy()
    expect(screen.getByText(/delta_vs_mean 0\.07500000000000001/)).toBeTruthy()
    expect(screen.getByText(/norm_pos 2/)).toBeTruthy()
    expect(screen.getByRole('img', { name: 'fhv1 input vector overlay' })).toBeTruthy()
    expect(screen.queryByText('0.1000')).toBeNull()
    expect(screen.queryByText(/0x3fc999999999999a/)).toBeNull()

    await user.click(screen.getByRole('checkbox', { name: 'Show all dimensions' }))
    expect(await screen.findByText(/0x3fc999999999999a/)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(await screen.findByRole('button', { name: 'trace-2' })).toBeTruthy()
    expect(calls.some((url) => url.includes('page=2'))).toBe(true)
  })

  it('renders the granularity comparison and the oob catch series', async () => {
    const compared = {
      ...detail,
      summary_metrics: {
        ...detail.summary_metrics,
        attribution: {
          in_domain_fail_counts: [0, 2],
          oob_catch_counts: [4, 0],
        },
        granularity_comparison: [
          {
            granularity: 'clauses',
            use_rogue_mask: true,
            evaluated_dims: 1015,
            confusion: {
              tp: 1,
              tn: 2,
              fp: 0,
              fn: 1,
              far_fpr: 0,
              frr_fnr: 0.30000000000000004,
              f1: null,
            },
          },
        ],
      },
    }
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      if (url.includes('/api/v1/fhv1/traces?')) {
        return jsonResponse({ page: 1, page_size: 20, total: 1, rows: [traceRow('trace-1')] })
      }
      if (url.includes('/api/v1/fhv1/benchmarks/')) return jsonResponse(compared)
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([run])
      return jsonResponse({})
    }
    render(<Fhv1BenchmarkExplorer fetchImpl={fetchImpl} store={memorySessionStore()} />)
    const table = await screen.findByRole('table', { name: 'Granularity comparison' })
    expect(table.textContent).toContain('Granularity & Mask Comparison')
    expect(table.textContent).toContain('clauses')
    expect(table.textContent).toContain('true')
    expect(table.textContent).toContain('1015')
    expect(table.textContent).toContain('0.30000000000000004')
    expect(table.textContent).toContain('null')
    expect(screen.queryByText('0.3000')).toBeNull()
    const tooltip = attributionOption([0, 2], [4, 0]).tooltip as { formatter?: (params: unknown) => string }
    expect(tooltip.formatter?.([{ dataIndex: 1 }])).toBe('dim 1\nin_domain_fail 2\noob_catch 0')
    await waitFor(() => {
      expect(charts.options.some((option) => option.series?.some((series) => series.name === 'oob_catch'))).toBe(true)
    })
    const painted = charts.options.find((option) => option.series?.some((series) => series.name === 'oob_catch'))
    expect(painted?.tooltip?.formatter?.([{ dataIndex: 0 }])).toBe('dim 0\nin_domain_fail 0\noob_catch 4')
    expect(painted?.tooltip?.formatter?.([{ dataIndex: 0 }])).not.toContain('4.0000')
  })

  it('resets to page 1 when the benchmark run changes and forwards the trace id', async () => {
    const user = userEvent.setup()
    const calls: string[] = []
    const opened: string[] = []
    const second = { ...run, run_id: 'bench-2' }
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      calls.push(url)
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
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([run, second])
      return jsonResponse({})
    }
    render(
      <Fhv1BenchmarkExplorer
        fetchImpl={fetchImpl}
        store={memorySessionStore()}
        onTraceId={(traceId) => opened.push(traceId)}
      />,
    )
    await user.click(await screen.findByRole('button', { name: 'trace-1' }))
    expect(opened).toEqual(['trace-1'])
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(await screen.findByRole('button', { name: 'trace-2' })).toBeTruthy()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Benchmark run' }), 'bench-2')
    await waitFor(() => {
      const traces = calls.filter((url) => url.includes('/api/v1/fhv1/traces?'))
      const last = traces[traces.length - 1] ?? ''
      expect(new URL(last).searchParams.get('page')).toBe('1')
      expect(new URL(last).searchParams.get('run_id')).toBe('bench-2')
    })
    expect(await screen.findByRole('button', { name: 'trace-1' })).toBeTruthy()
  })

  it('renders an empty run without a comparison table', async () => {
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([])
      return jsonResponse({ page: 1, page_size: 20, total: 0, rows: [] })
    }
    render(<Fhv1BenchmarkExplorer fetchImpl={fetchImpl} store={memorySessionStore()} />)
    expect(await screen.findByRole('option', { name: 'Select run' })).toBeTruthy()
    expect(screen.getAllByText('no rows')).toHaveLength(4)
    expect(screen.queryByRole('table', { name: 'Granularity comparison' })).toBeNull()
    expect(screen.queryByRole('img', { name: 'fhv1 attribution' })).toBeNull()
    expect(screen.queryByRole('img', { name: 'fhv1 failed dimensions histogram' })).toBeNull()
  })

  it('forwards category and passed filters in listFhv1Traces', async () => {
    const urls: string[] = []
    const fetchImpl: typeof fetch = async (input) => {
      urls.push(String(input))
      return jsonResponse({ page: 1, page_size: 20, total: 0, rows: [] })
    }
    await listFhv1Traces(
      'http://127.0.0.1:8088',
      { runId: 'bench-1', category: 'IN_DOMAIN_VALID', passed: false, page: 2, pageSize: 20 },
      fetchImpl,
    )
    await listFhv1Traces('http://127.0.0.1:8088', { runId: 'bench-1', passed: true }, fetchImpl)
    await listFhv1Traces('http://127.0.0.1:8088', { runId: 'bench-1' }, fetchImpl)

    const first = new URL(urls[0] ?? '').searchParams
    expect(first.get('category')).toBe('IN_DOMAIN_VALID')
    expect(first.get('passed')).toBe('false')
    expect(first.get('page')).toBe('2')

    const second = new URL(urls[1] ?? '').searchParams
    expect(second.get('category')).toBeNull()
    expect(second.get('passed')).toBe('true')

    const third = new URL(urls[2] ?? '').searchParams
    expect(third.get('category')).toBeNull()
    expect(third.get('passed')).toBeNull()
  })

  it('builds numerically sorted histogram options and 1024D vector overlay options', () => {
    const globalHist = { '10': 2, '0': 5, '2': 1 }
    const byCat = {
      IN_DOMAIN_VALID: { '0': 4 },
      OUT_OF_DOMAIN_BENIGN: { '2': 1, '10': 1 },
      HYBRID_BOUNDARY: { '0': 1 },
      ADVERSARIAL_FUZZING: { '10': 1 },
    }
    const globalOpt = failedDimsHistogramOption(globalHist, byCat, 'global') as {
      xAxis?: { data?: string[] }
      series?: { name?: string; type?: string; data?: number[] }[]
      tooltip?: { formatter?: (params: unknown) => string }
    }
    expect(globalOpt.xAxis?.data).toEqual(['0', '2', '10'])
    expect(globalOpt.series).toHaveLength(1)
    expect(globalOpt.series?.[0]?.data).toEqual([5, 1, 2])
    expect(globalOpt.tooltip?.formatter?.([{ dataIndex: 2 }])).toBe('failed_dims 10\ncount 2')

    const perCatOpt = failedDimsHistogramOption(globalHist, byCat, 'per_category') as {
      xAxis?: { data?: string[] }
      series?: { name?: string; type?: string; data?: number[] }[]
      tooltip?: { formatter?: (params: unknown) => string }
    }
    expect(perCatOpt.xAxis?.data).toEqual(['0', '2', '10'])
    expect(perCatOpt.series?.map((series) => series.name)).toEqual([
      'IN_DOMAIN_VALID',
      'OUT_OF_DOMAIN_BENIGN',
      'HYBRID_BOUNDARY',
      'ADVERSARIAL_FUZZING',
    ])
    expect(perCatOpt.series?.[0]?.data).toEqual([4, 0, 0])
    expect(perCatOpt.series?.[1]?.data).toEqual([0, 1, 1])
    expect(perCatOpt.tooltip?.formatter?.([{ dataIndex: 2 }])).toBe(
      [
        'failed_dims 10',
        'IN_DOMAIN_VALID 0',
        'OUT_OF_DOMAIN_BENIGN 1',
        'HYBRID_BOUNDARY 0',
        'ADVERSARIAL_FUZZING 1',
      ].join('\n'),
    )

    const dims = [
      {
        observed: 0.1,
        observed_bits_hex: '0x3fb999999999999a',
        min: 0.25,
        max: 0.75,
        mean: 0.5,
        status: 'underflow',
        violation_delta: 0.15000000000000002,
        delta_vs_mean: -0.4,
        norm_pos: -0.3,
      },
      {
        observed: 0.5,
        observed_bits_hex: '0x3fe0000000000000',
        min: 0.5,
        max: 0.5,
        mean: 0.5,
        status: 'in_bounds',
        violation_delta: 0,
        delta_vs_mean: 0,
        norm_pos: null,
      },
      {
        observed: 0.9,
        observed_bits_hex: '0x3feccccccccccccd',
        min: 0.1,
        max: 0.4,
        mean: 0.25,
        status: 'pruned_rogue',
        violation_delta: 0,
        delta_vs_mean: 0.65,
        norm_pos: 2.666666666666667,
      },
      {
        observed: 0.85,
        observed_bits_hex: '0x3feb333333333333',
        min: 0.25,
        max: 0.55,
        mean: 0.4,
        status: 'overflow',
        violation_delta: 0.30000000000000004,
        delta_vs_mean: 0.45,
        norm_pos: 2,
      },
    ]
    const vecOpt = drilldownVectorOption(dims) as {
      xAxis?: { data?: number[] }
      series?: {
        name?: string
        type?: string
        data?: (number | null)[]
        itemStyle?: { color?: string }
      }[]
      tooltip?: { formatter?: (params: unknown) => string }
    }
    expect(vecOpt.xAxis?.data).toEqual([0, 1, 2, 3])
    const observedSeries = vecOpt.series?.find((series) => series.name === 'observed')
    const rogueSeries = vecOpt.series?.find((series) => series.name === 'pruned_rogue')
    const breachSeries = vecOpt.series?.find((series) => series.name === 'breach')
    const meanSeries = vecOpt.series?.find((series) => series.name === 'mean')
    expect(meanSeries?.data).toEqual([0.5, 0.5, 0.25, 0.4])
    expect(observedSeries?.data).toEqual([0.1, 0.5, null, 0.85])
    expect(rogueSeries?.data).toEqual([null, null, 0.9, null])
    expect(breachSeries?.itemStyle?.color).toBe('#ef4444')
    expect(breachSeries?.data).toEqual([0.1, null, null, 0.85])

    const underflowTip = vecOpt.tooltip?.formatter?.([{ dataIndex: 0 }]) ?? ''
    expect(underflowTip).toContain('dim 0')
    expect(underflowTip).toContain('status underflow')
    expect(underflowTip).toContain('x 0.1')
    expect(underflowTip).toContain('min 0.25')
    expect(underflowTip).toContain('max 0.75')
    expect(underflowTip).toContain('mean 0.5')
    expect(underflowTip).toContain('violation_delta underflow min-x=0.15000000000000002')
    expect(underflowTip).toContain('delta_vs_mean -0.4')
    expect(underflowTip).toContain('norm_pos -0.3')
    expect(underflowTip).not.toContain('0.1500\n')

    const nullNormTip = vecOpt.tooltip?.formatter?.([{ dataIndex: 1 }]) ?? ''
    expect(nullNormTip).toContain('violation_delta 0')
    expect(nullNormTip).toContain('norm_pos null')

    const overflowTip = vecOpt.tooltip?.formatter?.([{ dataIndex: 3 }]) ?? ''
    expect(overflowTip).toContain('violation_delta overflow x-max=0.30000000000000004')
  })

  it('toggles histogram mode, filters traces with page=1 reset, and selects multi-chunk drilldown', async () => {
    const user = userEvent.setup()
    const calls: string[] = []
    const histogramDetail = {
      ...detail,
      summary_metrics: {
        ...detail.summary_metrics,
        failed_dims_count_histogram: { '0': 2, '10': 1 },
        failed_dims_count_histogram_by_category: {
          IN_DOMAIN_VALID: { '0': 2 },
          OUT_OF_DOMAIN_BENIGN: { '10': 1 },
          HYBRID_BOUNDARY: {},
          ADVERSARIAL_FUZZING: {},
        },
      },
    }
    const multiDrill = {
      trace_id: 'trace-1',
      profile_id: 'python-v1-abc',
      chunks: [
        drill.chunks[0]!,
        {
          chunk_index: 1,
          chunk_strategy: 'clause',
          chunk_text: 'segunda clausula',
          chunk_passed: false,
          dimensions: [
            {
              observed: 0.01,
              observed_bits_hex: '0x3f847ae147ae147b',
              min: 0.1,
              max: 0.9,
              mean: 0.5,
              status: 'underflow',
              violation_delta: 0.09,
              delta_vs_mean: -0.49,
              norm_pos: -0.1125,
            },
          ],
        },
      ],
    }
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      calls.push(url)
      if (url.includes('/api/v1/fhv1/traces/')) return jsonResponse(multiDrill)
      if (url.includes('/api/v1/fhv1/traces?')) {
        const parsedUrl = new URL(url)
        const page = Number(parsedUrl.searchParams.get('page') ?? '1')
        const category = parsedUrl.searchParams.get('category') ?? 'IN_DOMAIN_VALID'
        const passed = parsedUrl.searchParams.get('passed')
        return jsonResponse({
          page,
          page_size: 20,
          total: 21,
          rows: [
            {
              ...traceRow(page === 1 ? 'trace-1' : 'trace-2'),
              category,
              overall_passed: passed === 'true',
            },
          ],
        })
      }
      if (url.includes('/api/v1/fhv1/benchmarks/')) return jsonResponse(histogramDetail)
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([run])
      return jsonResponse({})
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

    expect(await screen.findByRole('img', { name: 'fhv1 failed dimensions histogram' })).toBeTruthy()
    await waitFor(() => {
      expect(
        charts.options.some((option) =>
          option.series?.some((series) => series.name === 'failed_dims_count'),
        ),
      ).toBe(true)
    })

    await user.click(screen.getByRole('button', { name: 'Per-category overlay' }))
    await waitFor(() => {
      expect(
        charts.options.some((option) =>
          option.series?.some((series) => series.name === 'ADVERSARIAL_FUZZING'),
        ),
      ).toBe(true)
    })

    await user.selectOptions(screen.getByRole('combobox', { name: 'Drill-down chunk' }), '1')
    expect(await screen.findByText(/0x3f847ae147ae147b/)).toBeTruthy()
    expect(screen.getByText(/underflow min-x=0\.09/)).toBeTruthy()
    expect(screen.getByText(/norm_pos -0\.1125/)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(await screen.findByRole('button', { name: 'trace-2' })).toBeTruthy()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter category' }), 'OUT_OF_DOMAIN_BENIGN')
    await waitFor(() => {
      const traces = calls.filter((url) => url.includes('/api/v1/fhv1/traces?'))
      const last = new URL(traces[traces.length - 1] ?? '').searchParams
      expect(last.get('category')).toBe('OUT_OF_DOMAIN_BENIGN')
      expect(last.get('page')).toBe('1')
    })
    expect(await screen.findByText(/page 1 \//)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(await screen.findByText(/page 2 \//)).toBeTruthy()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter verdict' }), 'PASS')
    await waitFor(() => {
      const traces = calls.filter((url) => url.includes('/api/v1/fhv1/traces?'))
      const last = new URL(traces[traces.length - 1] ?? '').searchParams
      expect(last.get('category')).toBe('OUT_OF_DOMAIN_BENIGN')
      expect(last.get('passed')).toBe('true')
      expect(last.get('page')).toBe('1')
    })

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter verdict' }), 'FAIL')
    await waitFor(() => {
      const traces = calls.filter((url) => url.includes('/api/v1/fhv1/traces?'))
      const last = new URL(traces[traces.length - 1] ?? '').searchParams
      expect(last.get('passed')).toBe('false')
      expect(last.get('page')).toBe('1')
    })
  })
})
