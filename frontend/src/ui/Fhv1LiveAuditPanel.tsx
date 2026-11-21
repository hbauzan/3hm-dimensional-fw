import { useEffect, useState } from 'react'
import { formatLosslessF64, type Fhv1TraceSummary } from '../domain/fhv1.ts'
import { listFhv1Traces } from '../gateway/fhv1Client.ts'

export function Fhv1LiveAuditPanel({
  gatewayBase,
  profileId,
  refreshKey,
  fetchImpl,
  onOpenTrace,
}: {
  gatewayBase: string
  profileId: string
  refreshKey: number
  fetchImpl?: typeof fetch
  onOpenTrace?: (traceId: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<Fhv1TraceSummary[]>([])
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void listFhv1Traces(
      gatewayBase,
      { profileId: profileId.trim() || undefined, page: 1, pageSize: 20 },
      fetchImpl,
    ).then((parsed) => {
      if (cancelled) return
      if (!parsed.ok) {
        setRows([])
        setMessage(parsed.message)
        return
      }
      setRows(parsed.value.rows)
      setMessage(parsed.value.rows.length === 0 ? 'No fhv1 traces' : null)
    })
    return () => {
      cancelled = true
    }
  }, [open, gatewayBase, profileId, refreshKey, fetchImpl])

  return (
    <section aria-label="Live audit" className="border border-studio-line">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="fhv1-live-audit"
        className="w-full px-2 py-1 text-left text-[10px] uppercase tracking-wide text-studio-muted hover:text-studio-text"
        onClick={() => setOpen((current) => !current)}
      >
        Live audit
      </button>
      {open ? (
        <div id="fhv1-live-audit" className="border-t border-studio-line px-2 py-1">
          {message ? <p className="text-[10px] text-studio-muted">{message}</p> : null}
          <ul aria-label="fhv1 traces" className="flex flex-col gap-1">
            {rows.map((row) => (
              <li
                key={`${row.trace_id}-${row.chunk_index}`}
                className="font-mono text-[10px] text-studio-text"
              >
                {row.source_kind} {row.overall_passed ? 'PASS' : 'BREACH'}{' '}
                {formatLosslessF64(row.max_violation_delta)}
                {onOpenTrace ? (
                  <button type="button" className="ml-2 text-studio-accent" onClick={() => onOpenTrace(row.trace_id)}>
                    Open trace {row.trace_id}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
