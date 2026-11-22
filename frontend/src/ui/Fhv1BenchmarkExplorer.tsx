import { useEffect, useMemo, useState } from 'react'
import {
  FHV1_QUADRANTS,
  formatLosslessF64,
  formatViolationMagnitudeDirection,
  type Fhv1BenchmarkDetail,
  type Fhv1BenchmarkSummary,
  type Fhv1Confusion,
  type Fhv1DimView,
  type Fhv1Drilldown,
  type Fhv1GranularityComparison,
  type Fhv1TraceSummary,
} from '../domain/fhv1.ts'
import { browserSessionStore, loadSession, type SessionStore } from '../domain/session.ts'
import {
  getFhv1Benchmark,
  getFhv1Trace,
  listFhv1Benchmarks,
  listFhv1Traces,
} from '../gateway/fhv1Client.ts'
import {
  attributionOption,
  drilldownVectorOption,
  failedDimsHistogramOption,
  type Fhv1HistogramMode,
} from './fhv1Charts.ts'
import { Fhv1EChartsCanvas } from './Fhv1EChartsCanvas.tsx'

const browserStore = browserSessionStore()

type VerdictFilter = 'ALL' | 'PASS' | 'FAIL'

export function Fhv1BenchmarkExplorer({
  fetchImpl,
  store = browserStore,
  traceId = null,
  onTraceId,
}: {
  fetchImpl?: typeof fetch
  store?: SessionStore
  traceId?: string | null
  onTraceId?: (traceId: string) => void
}) {
  const [gatewayBase] = useState(() => loadSession(store).gatewayBase)
  const [runs, setRuns] = useState<Fhv1BenchmarkSummary[]>([])
  const [runId, setRunId] = useState('')
  const [detail, setDetail] = useState<Fhv1BenchmarkDetail | null>(null)
  const [histogramMode, setHistogramMode] = useState<Fhv1HistogramMode>('global')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('ALL')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [rows, setRows] = useState<Fhv1TraceSummary[]>([])
  const [drill, setDrill] = useState<Fhv1Drilldown | null>(null)
  const [chunkSelection, setChunkSelection] = useState<{ traceId: string | null; chunkIndex: number }>({
    traceId: null,
    chunkIndex: 0,
  })
  const [showAll, setShowAll] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void listFhv1Benchmarks(gatewayBase, fetchImpl).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setMessage(parsed.message)
        return
      }
      setRuns(parsed.value)
      setRunId((current) => current || parsed.value[0]?.run_id || '')
    })
    return () => {
      cancelled = true
    }
  }, [gatewayBase, fetchImpl])

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    void getFhv1Benchmark(gatewayBase, runId, fetchImpl).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setDetail(null)
        setMessage(parsed.message)
        return
      }
      setDetail(parsed.value)
      setMessage(null)
    })
    return () => {
      cancelled = true
    }
  }, [gatewayBase, runId, fetchImpl])

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    const category = categoryFilter === 'ALL' ? undefined : categoryFilter
    const passed = verdictFilter === 'ALL' ? undefined : verdictFilter === 'PASS'
    void listFhv1Traces(gatewayBase, { runId, category, passed, page, pageSize: 20 }, fetchImpl).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setRows([])
        setMessage(parsed.message)
        return
      }
      setRows(parsed.value.rows)
      setTotal(parsed.value.total)
    })
    return () => {
      cancelled = true
    }
  }, [gatewayBase, runId, categoryFilter, verdictFilter, page, fetchImpl])

  useEffect(() => {
    if (!traceId) return
    let cancelled = false
    void getFhv1Trace(gatewayBase, traceId, fetchImpl).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setDrill(null)
        setMessage(parsed.message)
        return
      }
      setDrill(parsed.value)
    })
    return () => {
      cancelled = true
    }
  }, [gatewayBase, traceId, fetchImpl])

  const visibleDrill = drill && drill.trace_id === traceId ? drill : null
  const activeChunkIndex =
    visibleDrill && chunkSelection.traceId === visibleDrill.trace_id ? chunkSelection.chunkIndex : 0
  const activeChunk = useMemo(() => {
    if (!visibleDrill || visibleDrill.chunks.length === 0) return null
    return (
      visibleDrill.chunks.find((chunk) => chunk.chunk_index === activeChunkIndex) ??
      visibleDrill.chunks[0] ??
      null
    )
  }, [visibleDrill, activeChunkIndex])
  const histogram = useMemo(() => {
    if (!detail?.failed_dims_count_histogram && !detail?.failed_dims_count_histogram_by_category) {
      return null
    }
    return failedDimsHistogramOption(
      detail.failed_dims_count_histogram,
      detail.failed_dims_count_histogram_by_category,
      histogramMode,
    )
  }, [detail, histogramMode])
  const overlay = useMemo(() => {
    if (!detail?.in_domain_fail_counts && !detail?.oob_catch_counts) return null
    return attributionOption(detail.in_domain_fail_counts ?? [], detail.oob_catch_counts)
  }, [detail])
  const vectorOverlay = useMemo(() => {
    if (!activeChunk || activeChunk.dimensions.length === 0) return null
    return drilldownVectorOption(activeChunk.dimensions)
  }, [activeChunk])
  const pageCount = Math.max(1, Math.ceil(total / 20))

  return (
    <section aria-label="Benchmark explorer" className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-studio-bg p-3 text-xs text-studio-text">
      <label className="flex max-w-md flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
        Benchmark run
        <select
          aria-label="Benchmark run"
          className="border border-studio-line bg-studio-bg px-1.5 py-0.5"
          value={runId}
          onChange={(event) => {
            setRunId(event.target.value)
            setPage(1)
          }}
        >
          <option value="">Select run</option>
          {runs.map((run) => (
            <option key={run.run_id} value={run.run_id}>
              {run.run_id}
            </option>
          ))}
        </select>
      </label>
      {message ? <p className="text-studio-warn">{message}</p> : null}
      {detail?.confusion ? <ConfusionGrid confusion={detail.confusion} title="Confusion" /> : null}
      <div className="grid gap-2 md:grid-cols-4">
        {FHV1_QUADRANTS.map((name) => {
          const confusion = detail?.per_category[name]
          return (
            <article key={name} aria-label={name} className="border border-studio-line bg-studio-card p-2">
              <h2 className="text-[10px] uppercase tracking-wide text-studio-muted">{name}</h2>
              {confusion ? <ConfusionLines confusion={confusion} /> : <p className="text-studio-muted">no rows</p>}
            </article>
          )
        })}
      </div>
      {detail?.granularity_comparison && detail.granularity_comparison.length > 0 ? (
        <ComparisonTable rows={detail.granularity_comparison} />
      ) : null}
      {histogram ? (
        <section aria-label="Failed dimensions distribution" className="flex flex-col gap-2 border border-studio-line p-2">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-studio-muted">
            <span>Failed dims histogram</span>
            <button
              type="button"
              aria-pressed={histogramMode === 'global'}
              className="border border-studio-line px-2 py-0.5 text-studio-text"
              onClick={() => setHistogramMode('global')}
            >
              Global
            </button>
            <button
              type="button"
              aria-pressed={histogramMode === 'per_category'}
              className="border border-studio-line px-2 py-0.5 text-studio-text"
              onClick={() => setHistogramMode('per_category')}
            >
              Per-category overlay
            </button>
          </div>
          <Fhv1EChartsCanvas option={histogram} label="fhv1 failed dimensions histogram" />
        </section>
      ) : null}
      {overlay ? <Fhv1EChartsCanvas option={overlay} label="fhv1 attribution" /> : null}
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Category
          <select
            aria-label="Filter category"
            className="border border-studio-line bg-studio-bg px-1.5 py-0.5"
            value={categoryFilter}
            onChange={(event) => {
              setCategoryFilter(event.target.value)
              setPage(1)
            }}
          >
            <option value="ALL">ALL</option>
            {FHV1_QUADRANTS.map((quadrant) => (
              <option key={quadrant} value={quadrant}>
                {quadrant}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Verdict
          <select
            aria-label="Filter verdict"
            className="border border-studio-line bg-studio-bg px-1.5 py-0.5"
            value={verdictFilter}
            onChange={(event) => {
              const value = event.target.value
              if (value === 'ALL' || value === 'PASS' || value === 'FAIL') {
                setVerdictFilter(value)
                setPage(1)
              }
            }}
          >
            <option value="ALL">ALL</option>
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
          </select>
        </label>
      </div>
      <div className="overflow-auto border border-studio-line">
        <table aria-label="fhv1 audit traces" className="w-full border-collapse font-mono text-[10px]">
          <thead>
            <tr>
              {['trace', 'source', 'category', 'decision', 'failed', 'delta'].map((label) => (
                <th key={label} className="border-b border-studio-line px-1 py-1 text-left uppercase text-studio-muted">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.trace_id}-${row.chunk_index}`}>
                <td className="px-1 py-0.5">
                  <button type="button" className="text-studio-accent" onClick={() => onTraceId?.(row.trace_id)}>
                    {row.trace_id}
                  </button>
                </td>
                <td className="px-1 py-0.5">{row.source_kind}</td>
                <td className="px-1 py-0.5">{row.category ?? ''}</td>
                <td className="px-1 py-0.5">{row.overall_passed ? 'PASS' : 'BREACH'}</td>
                <td className="px-1 py-0.5">{formatLosslessF64(row.failed_dims_count)}</td>
                <td className="px-1 py-0.5">{formatLosslessF64(row.max_violation_delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-studio-muted">
        <button type="button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          Previous page
        </button>
        <span>
          page {page} / {pageCount}
        </span>
        <button type="button" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>
          Next page
        </button>
      </div>
      {visibleDrill ? (
        <section aria-label="fhv1 drill-down" className="border border-studio-line p-2 font-mono text-[10px]">
          <p>
            {visibleDrill.trace_id} · {visibleDrill.profile_id}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-1 uppercase text-studio-muted">
              <input type="checkbox" checked={showAll} onChange={(event) => setShowAll(event.target.checked)} />
              Show all dimensions
            </label>
            {visibleDrill.chunks.length > 1 ? (
              <label className="flex items-center gap-1 uppercase text-studio-muted">
                Chunk
                <select
                  aria-label="Drill-down chunk"
                  className="border border-studio-line bg-studio-bg px-1.5 py-0.5 text-studio-text"
                  value={activeChunk?.chunk_index ?? 0}
                  onChange={(event) =>
                    setChunkSelection({
                      traceId: visibleDrill.trace_id,
                      chunkIndex: Number(event.target.value),
                    })
                  }
                >
                  {visibleDrill.chunks.map((chunk) => (
                    <option key={chunk.chunk_index} value={chunk.chunk_index}>
                      chunk {chunk.chunk_index} ({chunk.chunk_strategy})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          {vectorOverlay ? <Fhv1EChartsCanvas option={vectorOverlay} label="fhv1 input vector overlay" /> : null}
          {activeChunk ? (
            <div className="mt-2">
              <p>
                chunk {activeChunk.chunk_index} {activeChunk.chunk_strategy}{' '}
                {activeChunk.chunk_passed ? 'PASS' : 'BREACH'}
              </p>
              {visibleDims(activeChunk.dimensions, showAll).map((dim) => (
                <p key={dim.index}>
                  dim {dim.index} {dim.status} {formatLosslessF64(dim.observed)} {dim.observed_bits_hex} mean{' '}
                  {formatLosslessF64(dim.mean)} delta {formatViolationMagnitudeDirection(dim)} delta_vs_mean{' '}
                  {formatLosslessF64(dim.delta_vs_mean)} norm_pos{' '}
                  {dim.norm_pos === null ? 'null' : formatLosslessF64(dim.norm_pos)}
                </p>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  )
}

function ComparisonTable({ rows }: { rows: readonly Fhv1GranularityComparison[] }) {
  const columns = [
    'granularity',
    'use_rogue_mask',
    'evaluated_dims',
    'tp',
    'tn',
    'fp',
    'fn',
    'far_fpr',
    'frr_fnr',
    'f1',
  ] as const
  return (
    <div className="overflow-auto border border-studio-line">
      <table aria-label="Granularity comparison" className="w-full border-collapse font-mono text-[10px]">
        <caption className="px-1 py-1 text-left text-[10px] uppercase tracking-wide text-studio-muted">
          Granularity & Mask Comparison
        </caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-studio-line px-1 py-1 text-left uppercase text-studio-muted">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.granularity}-${String(row.use_rogue_mask)}-${index}`}>
              <td className="px-1 py-0.5">{row.granularity}</td>
              <td className="px-1 py-0.5">{String(row.use_rogue_mask)}</td>
              <td className="px-1 py-0.5">{formatLosslessF64(row.evaluated_dims)}</td>
              <td className="px-1 py-0.5">{formatLosslessF64(row.tp)}</td>
              <td className="px-1 py-0.5">{formatLosslessF64(row.tn)}</td>
              <td className="px-1 py-0.5">{formatLosslessF64(row.fp)}</td>
              <td className="px-1 py-0.5">{formatLosslessF64(row.fn)}</td>
              <td className="px-1 py-0.5">{shownRate(row.far_fpr)}</td>
              <td className="px-1 py-0.5">{shownRate(row.frr_fnr)}</td>
              <td className="px-1 py-0.5">{shownRate(row.f1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function shownRate(value: number | null): string {
  return value === null ? 'null' : formatLosslessF64(value)
}

function ConfusionGrid({ confusion, title }: { confusion: Fhv1Confusion; title: string }) {
  return (
    <section aria-label={title} className="grid grid-cols-2 gap-2 md:grid-cols-4">
      <Count label="True positive" value={confusion.tp} />
      <Count label="True negative" value={confusion.tn} />
      <Count label="False positive" value={confusion.fp} />
      <Count label="False negative" value={confusion.fn} />
    </section>
  )
}

function ConfusionLines({ confusion }: { confusion: Fhv1Confusion }) {
  return (
    <div className="font-mono">
      <p>tp {formatLosslessF64(confusion.tp)}</p>
      <p>tn {formatLosslessF64(confusion.tn)}</p>
      <p>fp {formatLosslessF64(confusion.fp)}</p>
      <p>fn {formatLosslessF64(confusion.fn)}</p>
      <p>far {formatRate(confusion.far_fpr)}</p>
      <p>frr {formatRate(confusion.frr_fnr)}</p>
    </div>
  )
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <article aria-label={label} className="border border-studio-line bg-studio-card p-2">
      <h2 className="text-[10px] uppercase tracking-wide text-studio-muted">{label}</h2>
      <p className="font-mono text-sm">{formatLosslessF64(value)}</p>
    </article>
  )
}

function formatRate(value: number | null): string {
  return value === null ? 'null' : formatLosslessF64(value)
}

function visibleDims(dimensions: readonly Fhv1DimView[], showAll: boolean): (Fhv1DimView & { index: number })[] {
  return dimensions.flatMap((dim, index) =>
    showAll || index === 0 || dim.status !== 'in_bounds' ? [{ ...dim, index }] : [],
  )
}
