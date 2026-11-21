import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Fhv1ProfileDetail } from '../domain/fhv1.ts'
import { memorySessionStore } from '../domain/session.ts'
import { envelopeOption, envelopeTooltip } from './fhv1Charts.ts'
import { Fhv1VarianceStudio } from './Fhv1VarianceStudio.tsx'

const written = vi.hoisted(() => ({ values: [] as string[] }))

vi.mock('../domain/fhv1.ts', async () => {
  const actual = await vi.importActual<typeof import('../domain/fhv1.ts')>('../domain/fhv1.ts')
  return {
    ...actual,
    writeExactText: (text: string) => {
      written.values.push(text)
      return Promise.resolve()
    },
  }
})

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

const summary = {
  profile_id: 'python-v1-abc',
  policy_id: 'python',
  sample_count: 2,
  normalize: true,
  use_rogue_mask_default: false,
}

const detail: Fhv1ProfileDetail = {
  ...summary,
  min: [0.1, 0.2],
  max: [0.3, 0.4],
  mean: [0.15, 0.25],
  span: [0.2, 0.2],
  variance: [0.30000000000000004, 0.01],
  std_dev: [0.5, 0.1],
  movement_tier_codes: [0, 4],
  quantile_cutoffs: { p25: 0.25, p75: 0.75, p90: 0.9 },
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('Fhv1VarianceStudio', () => {
  beforeEach(() => {
    written.values.length = 0
    URL.createObjectURL = () => 'blob:fhv1'
    URL.revokeObjectURL = () => undefined
  })

  it('renders lossless coordinates, sorts, filters, calibrates, and exports', async () => {
    const user = userEvent.setup()
    const calls: { url: string; body: unknown }[] = []
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = String(input)
      const raw = init?.body
      calls.push({ url, body: typeof raw === 'string' ? JSON.parse(raw) : null })
      if (url.includes('/export?')) {
        return new Response('csv', {
          status: 200,
          headers: { 'content-disposition': 'attachment; filename="profile.csv"' },
        })
      }
      if (url.endsWith('/api/v1/fhv1/calibrate')) return jsonResponse(200, summary)
      if (url.endsWith('/api/v1/fhv1/profiles')) return jsonResponse(200, [summary])
      if (url.includes('/api/v1/fhv1/profiles/')) return jsonResponse(200, detail)
      return jsonResponse(404, { error: url })
    }

    render(<Fhv1VarianceStudio fetchImpl={fetchImpl} store={memorySessionStore()} />)
    expect(await screen.findByText('0.30000000000000004')).toBeTruthy()
    expect(screen.queryByText('0.3000')).toBeNull()
    expect(screen.getByRole('img', { name: 'fhv1 envelope' })).toBeTruthy()
    expect(
      calls.some(
        (call) =>
          call.url.includes('metric=span') &&
          call.url.includes('p25=0.25') &&
          call.url.includes('p75=0.75') &&
          call.url.includes('p90=0.90'),
      ),
    ).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Copy variance 0' }))
    expect(written.values).toEqual(['0.30000000000000004'])

    await user.click(screen.getByRole('button', { name: 'variance' }))
    const sorted = screen.getAllByRole('row').slice(1)
    expect(sorted[0]?.textContent).toContain('0.01')

    await user.type(screen.getByRole('textbox', { name: 'Filter dimensions' }), 'ExtremeMovement')
    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(screen.getByText('ExtremeMovement')).toBeTruthy()

    await user.type(screen.getByRole('textbox', { name: 'Calibration texts' }), 'hola fhv1')
    await user.click(screen.getByRole('button', { name: 'Calibrate profile' }))
    const posted = calls.find((call) => call.url.endsWith('/api/v1/fhv1/calibrate'))
    expect(posted?.body).toEqual({
      policy_id: 'python',
      texts: ['hola fhv1'],
      normalize: true,
      use_rogue_mask_default: false,
    })

    await user.click(screen.getByRole('button', { name: 'Export csv' }))
    expect(calls.some((call) => call.url.includes('/export?format=csv'))).toBe(true)
  })

  it('keeps the envelope tooltip and data zoom on raw f64 text', () => {
    expect(envelopeTooltip(detail, [{ dataIndex: 0 }])).toBe('dim 0\nmin 0.1\nmax 0.3\nmean 0.15')
    const option = envelopeOption(detail) as { dataZoom?: unknown[]; tooltip?: { formatter?: (params: unknown) => string } }
    expect(option.dataZoom).toHaveLength(2)
    expect(option.tooltip?.formatter?.([{ dataIndex: 1 }])).toBe('dim 1\nmin 0.2\nmax 0.4\nmean 0.25')
    expect(option.tooltip?.formatter?.([{ dataIndex: 0 }])).not.toContain('0.1000')
  })

  it('switches movement metrics and accepts the closed quantile interval', async () => {
    const user = userEvent.setup()
    const calls: string[] = []
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      calls.push(url)
      if (url.endsWith('/api/v1/fhv1/profiles')) return jsonResponse(200, [summary])
      if (url.includes('/api/v1/fhv1/profiles/')) return jsonResponse(200, detail)
      return jsonResponse(404, { error: url })
    }
    render(<Fhv1VarianceStudio fetchImpl={fetchImpl} store={memorySessionStore()} />)
    expect(await screen.findByText('0.30000000000000004')).toBeTruthy()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Movement metric' }), 'variance')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Movement metric' }), 'std_dev')
    await user.clear(screen.getByRole('textbox', { name: 'P25' }))
    await user.type(screen.getByRole('textbox', { name: 'P25' }), '0')
    await user.tab()
    await user.clear(screen.getByRole('textbox', { name: 'P90' }))
    await user.type(screen.getByRole('textbox', { name: 'P90' }), '1')
    await user.tab()
    await waitFor(() => {
      expect(calls.some((url) => queryOf(url).get('metric') === 'variance')).toBe(true)
      expect(
        calls.some((url) => {
          const query = queryOf(url)
          return query.get('metric') === 'std_dev' && query.get('p25') === '0' && query.get('p90') === '1'
        }),
      ).toBe(true)
    })

    await user.clear(screen.getByRole('textbox', { name: 'P25' }))
    await user.type(screen.getByRole('textbox', { name: 'P25' }), '0.9')
    await user.tab()
    expect(await screen.findByText('quantiles must satisfy 0 <= P25 < P75 < P90 <= 1')).toBeTruthy()
    expect(calls.some((url) => queryOf(url).get('p25') === '0.9')).toBe(false)
  })

  it('uploads a calibration file, exports xlsx and parquet, and filters rogue rows', async () => {
    const user = userEvent.setup()
    const calls: { url: string; body: unknown }[] = []
    const rogueDetail: Fhv1ProfileDetail = {
      ...detail,
      min: filled(0),
      max: filled(1),
      mean: filled(0),
      span: filled(1),
      variance: filled(0, 292, 0.30000000000000004),
      std_dev: filled(0),
      movement_tier_codes: filled(0),
    }
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = String(input)
      const raw = init?.body
      calls.push({ url, body: typeof raw === 'string' ? JSON.parse(raw) : null })
      if (url.includes('/export?')) {
        return new Response('export', {
          status: 200,
          headers: { 'content-disposition': 'attachment; filename="profile.bin"' },
        })
      }
      if (url.endsWith('/api/v1/fhv1/calibrate')) return jsonResponse(200, summary)
      if (url.endsWith('/api/v1/fhv1/profiles')) return jsonResponse(200, [summary])
      if (url.includes('/api/v1/fhv1/profiles/')) return jsonResponse(200, rogueDetail)
      return jsonResponse(404, { error: url })
    }
    render(<Fhv1VarianceStudio fetchImpl={fetchImpl} store={memorySessionStore()} />)
    expect(await screen.findByText('0.30000000000000004')).toBeTruthy()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Movement metric' }), 'variance')
    await user.upload(
      screen.getByLabelText('Calibration file'),
      new File(['linea uno'], 'corpus.txt', { type: 'text/plain' }),
    )
    await waitFor(() => {
      expect((screen.getByRole('button', { name: 'Calibrate profile' }) as HTMLButtonElement).disabled).toBe(false)
    })
    await user.click(screen.getByRole('button', { name: 'Calibrate profile' }))
    const posted = calls.find((call) => call.url.endsWith('/api/v1/fhv1/calibrate'))
    expect(posted?.body).toEqual({
      policy_id: 'python',
      texts: ['linea uno'],
      normalize: true,
      use_rogue_mask_default: false,
    })

    await user.click(screen.getByRole('button', { name: 'Export xlsx' }))
    await user.click(screen.getByRole('button', { name: 'Export parquet' }))
    expect(calls.some((call) => call.url.includes('/export?format=xlsx'))).toBe(true)
    expect(calls.some((call) => call.url.includes('/export?format=parquet'))).toBe(true)

    await user.type(screen.getByRole('textbox', { name: 'Filter dimensions' }), 'yes')
    const rogueRows = screen.getAllByRole('row').slice(1)
    expect(rogueRows).toHaveLength(1)
    expect(rogueRows[0]?.textContent).toContain('292')
    expect(rogueRows[0]?.textContent).toContain('yes')
    expect(rogueRows[0]?.textContent).toContain('0.30000000000000004')
    expect(screen.queryByText('0.3000')).toBeNull()

    await user.clear(screen.getByRole('textbox', { name: 'Filter dimensions' }))
    await user.type(screen.getByRole('textbox', { name: 'Filter dimensions' }), '292')
    expect(screen.getAllByRole('row').slice(1)).toHaveLength(1)
    expect(screen.getByText('292')).toBeTruthy()
  })
})

function filled(value: number, at = -1, replacement = value): number[] {
  return Array.from({ length: 293 }, (_, index) => (index === at ? replacement : value))
}

function queryOf(url: string): URLSearchParams {
  return new URL(url).searchParams
}
