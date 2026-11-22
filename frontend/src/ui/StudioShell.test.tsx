import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { memorySessionStore } from '../domain/session.ts'
import { StudioShell } from './StudioShell.tsx'

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
  eval_granularity: 'clauses',
  use_rogue_mask: false,
  total_inputs: 1,
  total_chunks: 1,
}

const detail = {
  ...run,
  summary_metrics: {
    confusion: { tp: 1, tn: 0, fp: 0, fn: 0 },
  },
}

const drill = {
  trace_id: 'live-1',
  profile_id: 'python-v1-abc',
  chunks: [
    {
      chunk_index: 0,
      chunk_strategy: 'full_doc',
      chunk_text: 'hola',
      chunk_passed: true,
      dimensions: [
        {
          observed: 0.1,
          observed_bits_hex: '0x3fb999999999999a',
          min: 0,
          max: 1,
          mean: 0.5,
          status: 'in_bounds',
          violation_delta: 0,
          delta_vs_mean: -0.4,
          norm_pos: 0.1,
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

function sseResponse(chunks: readonly string[]): Response {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
        controller.close()
      },
    }),
    { status: 200, headers: { 'content-type': 'text/event-stream' } },
  )
}

describe('StudioShell', () => {
  it('keeps the playground transcript and opens a trace in the explorer', async () => {
    const user = userEvent.setup()
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input)
      if (url.includes('/api/v1/chat')) {
        return sseResponse([`data: ${JSON.stringify({ choices: [{ delta: { content: 'Hello' } }] })}\n\n`])
      }
      if (url.includes('/api/v1/fhv1/traces/')) return jsonResponse(drill)
      if (url.includes('/api/v1/fhv1/traces')) {
        return jsonResponse({
          page: 1,
          page_size: 20,
          total: 1,
          rows: [
            {
              trace_id: 'live-1',
              source_kind: 'REALTIME_CHAT',
              profile_id: 'python-v1-abc',
              chunk_index: 0,
              overall_passed: true,
              failed_dims_count: 0,
              max_violation_delta: 0,
            },
          ],
        })
      }
      if (url.includes('/api/v1/fhv1/benchmarks/')) return jsonResponse(detail)
      if (url.endsWith('/api/v1/fhv1/benchmarks')) return jsonResponse([run])
      if (url.includes('/api/v1/fhv1/profiles')) return jsonResponse([])
      return jsonResponse({ error: url })
    }
    const { container } = render(<StudioShell fetchImpl={fetchImpl} store={memorySessionStore()} />)

    expect(pressed('Playground')).toBe('true')
    expect(pressed('Variance studio')).toBe('false')
    expect(pressed('Benchmark explorer')).toBe('false')

    await user.type(screen.getByRole('textbox', { name: 'Prompt' }), 'hola')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('Hello')).toBeTruthy()
    expect(container.querySelector('aside')?.className).toContain('w-60')
    expect(screen.getByRole('list', { name: 'Messages' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Variance studio' }))
    expect(pressed('Variance studio')).toBe('true')
    expect(pressed('Playground')).toBe('false')
    expect(screen.queryByRole('list', { name: 'Messages' })).toBeNull()
    expect(screen.getByText('Hello').closest('[hidden]')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Playground' }))
    expect(screen.getByRole('list', { name: 'Messages' }).textContent).toContain('hola')
    expect(screen.getByText('Hello').closest('[hidden]')).toBeNull()
    expect(container.querySelector('aside')?.className).toContain('w-60')

    await user.click(screen.getByRole('button', { name: 'Live audit' }))
    await user.click(await screen.findByRole('button', { name: 'Open trace live-1' }))
    expect(pressed('Benchmark explorer')).toBe('true')
    expect(await screen.findByText('live-1 · python-v1-abc')).toBeTruthy()
    expect(screen.getByText(/0x3fb999999999999a/)).toBeTruthy()
    expect(screen.queryByRole('list', { name: 'Messages' })).toBeNull()
    expect(screen.getByText('Hello').closest('[hidden]')).toBeTruthy()
  })
})

function pressed(name: string): string | null {
  return screen.getByRole('button', { name }).getAttribute('aria-pressed')
}
