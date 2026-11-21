import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  FHV1_METRICS,
  formatLosslessF64,
  isFhv1Metric,
  writeExactText,
  isFhv1RogueDim,
  movementTierName,
  type Fhv1Metric,
  type Fhv1ProfileDetail,
  type Fhv1ProfileSummary,
} from '../domain/fhv1.ts'
import { browserSessionStore, loadSession, type SessionStore } from '../domain/session.ts'
import {
  downloadFhv1Export,
  getFhv1Profile,
  listFhv1Profiles,
  postFhv1Calibrate,
} from '../gateway/fhv1Client.ts'
import { envelopeOption, rankingOption, tierOption } from './fhv1Charts.ts'
import { Fhv1EChartsCanvas } from './Fhv1EChartsCanvas.tsx'

const browserStore = browserSessionStore()

type SortKey = 'dim' | 'min' | 'max' | 'mean' | 'span' | 'variance' | 'std_dev' | 'movement_tier'

interface EnvelopeRow {
  dim: number
  rogue: boolean
  min: number
  max: number
  mean: number
  span: number
  variance: number
  std_dev: number
  tier: string
  tierCode: number
}

export function Fhv1VarianceStudio({
  fetchImpl,
  store = browserStore,
}: {
  fetchImpl?: typeof fetch
  store?: SessionStore
}) {
  const [gatewayBase] = useState(() => loadSession(store).gatewayBase)
  const [profiles, setProfiles] = useState<Fhv1ProfileSummary[]>([])
  const [profileId, setProfileId] = useState('')
  const [metric, setMetric] = useState<Fhv1Metric>('span')
  const [p25, setP25] = useState('0.25')
  const [p75, setP75] = useState('0.75')
  const [p90, setP90] = useState('0.90')
  const [applied, setApplied] = useState({ p25: '0.25', p75: '0.75', p90: '0.90' })
  const [detail, setDetail] = useState<Fhv1ProfileDetail | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [policyId, setPolicyId] = useState('python')
  const [corpus, setCorpus] = useState('')
  const [fileText, setFileText] = useState('')
  const [normalize, setNormalize] = useState(true)
  const [rogueDefault, setRogueDefault] = useState(false)
  const [filter, setFilter] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('dim')
  const [sortAsc, setSortAsc] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    void listFhv1Profiles(gatewayBase, fetchImpl).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setMessage(parsed.message)
        return
      }
      setProfiles(parsed.value)
      setProfileId((current) => current || parsed.value[0]?.profile_id || '')
    })
    return () => {
      cancelled = true
    }
  }, [gatewayBase, fetchImpl])

  useEffect(() => {
    if (!profileId) return
    let cancelled = false
    void getFhv1Profile(
      gatewayBase,
      profileId,
      { metric, p25: applied.p25, p75: applied.p75, p90: applied.p90 },
      fetchImpl,
    ).then((parsed) => {
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
  }, [gatewayBase, profileId, metric, applied, fetchImpl])

  const rows = useMemo(() => (detail ? sortRows(filterRows(buildRows(detail), filter), sortKey, sortAsc) : []), [detail, filter, sortKey, sortAsc])
  const envelope = useMemo(() => (detail ? envelopeOption(detail) : null), [detail])
  const ranking = useMemo(() => (detail ? rankingOption(detail, metric) : null), [detail, metric])
  const tiers = useMemo(() => (detail ? tierOption(detail) : null), [detail])

  function applyQuantiles() {
    if (!quantilesValid(p25, p75, p90)) {
      setMessage('quantiles must satisfy 0 < P25 < P75 < P90 < 1')
      return
    }
    setApplied({ p25, p75, p90 })
  }

  async function onCalibrate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const texts = [corpus, fileText].map((text) => text.trim()).filter((text) => text.length > 0)
    if (!policyId.trim() || texts.length === 0 || busy) return
    setBusy(true)
    const parsed = await postFhv1Calibrate(
      gatewayBase,
      {
        policyId: policyId.trim(),
        texts,
        normalize,
        useRogueMaskDefault: rogueDefault,
      },
      fetchImpl,
    )
    setBusy(false)
    if (!parsed.ok) {
      setMessage(parsed.message)
      return
    }
    setProfiles((current) =>
      current.some((profile) => profile.profile_id === parsed.value.profile_id)
        ? current
        : [parsed.value, ...current],
    )
    setProfileId(parsed.value.profile_id)
    setMessage(null)
  }

  async function onExport(format: 'xlsx' | 'csv' | 'parquet') {
    if (!profileId) return
    const parsed = await downloadFhv1Export(gatewayBase, profileId, format, fetchImpl)
    if (!parsed.ok) {
      setMessage(parsed.message)
      return
    }
    const href = URL.createObjectURL(parsed.value.blob)
    const anchor = document.createElement('a')
    anchor.href = href
    anchor.download = parsed.value.filename
    anchor.click()
    URL.revokeObjectURL(href)
  }

  function toggleSort(next: SortKey) {
    if (next === sortKey) setSortAsc((current) => !current)
    else {
      setSortKey(next)
      setSortAsc(true)
    }
  }

  return (
    <section aria-label="Variance studio" className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-studio-bg p-3 text-xs text-studio-text">
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          fhv1 profile
          <select
            aria-label="Studio profile"
            className="border border-studio-line bg-studio-bg px-1.5 py-0.5"
            value={profileId}
            onChange={(event) => setProfileId(event.target.value)}
          >
            <option value="">Select profile</option>
            {profiles.map((profile) => (
              <option key={profile.profile_id} value={profile.profile_id}>
                {profile.profile_id}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Movement metric
          <select
            aria-label="Movement metric"
            className="border border-studio-line bg-studio-bg px-1.5 py-0.5"
            value={metric}
            onChange={(event) => {
              if (isFhv1Metric(event.target.value)) setMetric(event.target.value)
            }}
          >
            {FHV1_METRICS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <Quantile label="P25" value={p25} onChange={setP25} onBlur={applyQuantiles} />
        <Quantile label="P75" value={p75} onChange={setP75} onBlur={applyQuantiles} />
        <Quantile label="P90" value={p90} onChange={setP90} onBlur={applyQuantiles} />
        <button type="button" className="border border-studio-line px-2 py-1 text-[10px] uppercase" disabled={!profileId} onClick={() => void onExport('xlsx')}>
          Export xlsx
        </button>
        <button type="button" className="border border-studio-line px-2 py-1 text-[10px] uppercase" disabled={!profileId} onClick={() => void onExport('csv')}>
          Export csv
        </button>
        <button type="button" className="border border-studio-line px-2 py-1 text-[10px] uppercase" disabled={!profileId} onClick={() => void onExport('parquet')}>
          Export parquet
        </button>
      </div>
      {detail ? (
        <p className="font-mono text-[10px] text-studio-muted">
          cutoffs {formatLosslessF64(detail.quantile_cutoffs.p25)} / {formatLosslessF64(detail.quantile_cutoffs.p75)} / {formatLosslessF64(detail.quantile_cutoffs.p90)}
        </p>
      ) : null}
      <form onSubmit={onCalibrate} className="flex flex-wrap items-end gap-2 border border-studio-line p-2">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Calibration policy
          <input aria-label="Calibration policy" className="border border-studio-line bg-studio-bg px-1.5 py-0.5" value={policyId} onChange={(event) => setPolicyId(event.target.value)} />
        </label>
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Calibration texts
          <textarea aria-label="Calibration texts" rows={2} className="border border-studio-line bg-studio-bg px-1.5 py-0.5" value={corpus} onChange={(event) => setCorpus(event.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          Calibration file
          <input
            aria-label="Calibration file"
            type="file"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (!file) return
              void file.text().then(setFileText)
            }}
          />
        </label>
        <label className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          <input type="checkbox" checked={normalize} onChange={(event) => setNormalize(event.target.checked)} />
          Normalize embeddings
        </label>
        <label className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
          <input type="checkbox" checked={rogueDefault} onChange={(event) => setRogueDefault(event.target.checked)} />
          Default rogue mask
        </label>
        <button type="submit" disabled={busy || (corpus.trim() === '' && fileText.trim() === '')} className="border border-studio-accent px-2 py-1 text-[10px] uppercase">
          {busy ? 'Calibrating' : 'Calibrate profile'}
        </button>
      </form>
      {message ? <p className="text-studio-warn">{message}</p> : null}
      {envelope ? <Fhv1EChartsCanvas option={envelope} label="fhv1 envelope" /> : null}
      {ranking ? <Fhv1EChartsCanvas option={ranking} label="fhv1 movement ranking" /> : null}
      {tiers ? <Fhv1EChartsCanvas option={tiers} label="fhv1 tier distribution" /> : null}
      <label className="flex max-w-64 flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
        Filter dimensions
        <input aria-label="Filter dimensions" className="border border-studio-line bg-studio-bg px-1.5 py-0.5" value={filter} onChange={(event) => setFilter(event.target.value)} />
      </label>
      <div className="overflow-auto border border-studio-line">
        <table aria-label="fhv1 envelope" className="w-full border-collapse font-mono text-[10px]">
          <thead>
            <tr>
              {(['dim', 'min', 'max', 'mean', 'span', 'variance', 'std_dev', 'movement_tier'] as const).map((key) => (
                <th key={key} className="border-b border-studio-line px-1 py-1 text-left">
                  <button type="button" className="uppercase text-studio-muted" onClick={() => toggleSort(key)}>
                    {key}
                  </button>
                </th>
              ))}
              <th className="border-b border-studio-line px-1 py-1 text-left uppercase text-studio-muted">is_rogue</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.dim}>
                <td className="px-1 py-0.5">{row.dim}</td>
                <NumberCell dim={row.dim} field="min" value={row.min} />
                <NumberCell dim={row.dim} field="max" value={row.max} />
                <NumberCell dim={row.dim} field="mean" value={row.mean} />
                <NumberCell dim={row.dim} field="span" value={row.span} />
                <NumberCell dim={row.dim} field="variance" value={row.variance} />
                <NumberCell dim={row.dim} field="std_dev" value={row.std_dev} />
                <td className="px-1 py-0.5">{row.tier}</td>
                <td className="px-1 py-0.5">{row.rogue ? 'yes' : 'no'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Quantile({
  label,
  value,
  onChange,
  onBlur,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  onBlur: () => void
}) {
  return (
    <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
      {label}
      <input aria-label={label} className="w-16 border border-studio-line bg-studio-bg px-1.5 py-0.5 font-mono" value={value} onChange={(event) => onChange(event.target.value)} onBlur={onBlur} />
    </label>
  )
}

function NumberCell({ dim, field, value }: { dim: number; field: string; value: number }) {
  const text = formatLosslessF64(value)
  return (
    <td className="px-1 py-0.5">
      {text}{' '}
      <button
        type="button"
        aria-label={`Copy ${field} ${dim}`}
        className="text-studio-accent"
        onClick={() => {
          void writeExactText(text)
        }}
      >
        copy
      </button>
    </td>
  )
}

function buildRows(detail: Fhv1ProfileDetail): EnvelopeRow[] {
  return detail.min.map((min, dim) => ({
    dim,
    rogue: isFhv1RogueDim(dim),
    min,
    max: detail.max[dim] ?? min,
    mean: detail.mean[dim] ?? min,
    span: detail.span[dim] ?? 0,
    variance: detail.variance[dim] ?? 0,
    std_dev: detail.std_dev[dim] ?? 0,
    tier: movementTierName(detail.movement_tier_codes[dim] ?? 0),
    tierCode: detail.movement_tier_codes[dim] ?? 0,
  }))
}

function filterRows(rows: EnvelopeRow[], filter: string): EnvelopeRow[] {
  const needle = filter.trim().toLowerCase()
  if (!needle) return rows
  return rows.filter((row) => {
    const rogue = row.rogue ? 'yes' : 'no'
    return String(row.dim).includes(needle) || row.tier.toLowerCase().includes(needle) || rogue.includes(needle)
  })
}

function sortRows(rows: EnvelopeRow[], key: SortKey, ascending: boolean): EnvelopeRow[] {
  const next = [...rows]
  next.sort((left, right) => {
    const delta = sortValue(left, key) - sortValue(right, key)
    return ascending ? delta : -delta
  })
  return next
}

function sortValue(row: EnvelopeRow, key: SortKey): number {
  if (key === 'movement_tier') return row.tierCode
  return row[key]
}

function quantilesValid(p25: string, p75: string, p90: string): boolean {
  const first = Number(p25)
  const second = Number(p75)
  const third = Number(p90)
  return Number.isFinite(first) && Number.isFinite(second) && Number.isFinite(third) && first > 0 && first < second && second < third && third < 1
}
