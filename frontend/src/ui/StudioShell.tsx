import { useState } from 'react'
import type { SessionStore } from '../domain/session.ts'
import { Fhv1BenchmarkExplorer } from './Fhv1BenchmarkExplorer.tsx'
import { Fhv1VarianceStudio } from './Fhv1VarianceStudio.tsx'
import { Playground } from './Playground.tsx'

type StudioView = 'playground' | 'variance' | 'benchmark'

export function StudioShell({
  fetchImpl,
  store,
}: {
  fetchImpl?: typeof fetch
  store?: SessionStore
}) {
  const [view, setView] = useState<StudioView>('playground')
  const [traceId, setTraceId] = useState<string | null>(null)
  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-studio-bg text-studio-text">
      <nav aria-label="Studio views" className="flex flex-shrink-0 gap-2 border-b border-studio-line px-3 py-1.5">
        <button
          type="button"
          aria-pressed={view === 'playground'}
          className="border border-studio-line px-2 py-0.5 text-[10px] uppercase tracking-wide text-studio-muted"
          onClick={() => setView('playground')}
        >
          Playground
        </button>
        <button
          type="button"
          aria-pressed={view === 'variance'}
          className="border border-studio-line px-2 py-0.5 text-[10px] uppercase tracking-wide text-studio-muted"
          onClick={() => setView('variance')}
        >
          Variance studio
        </button>
        <button
          type="button"
          aria-pressed={view === 'benchmark'}
          className="border border-studio-line px-2 py-0.5 text-[10px] uppercase tracking-wide text-studio-muted"
          onClick={() => setView('benchmark')}
        >
          Benchmark explorer
        </button>
      </nav>
      <div className={pane(view === 'playground')} hidden={view !== 'playground'}>
        <Playground
          fetchImpl={fetchImpl}
          store={store}
          fill
          onOpenTrace={(next) => {
            setTraceId(next)
            setView('benchmark')
          }}
        />
      </div>
      <div className={pane(view === 'variance')} hidden={view !== 'variance'}>
        <Fhv1VarianceStudio fetchImpl={fetchImpl} store={store} />
      </div>
      <div className={pane(view === 'benchmark')} hidden={view !== 'benchmark'}>
        <Fhv1BenchmarkExplorer
          fetchImpl={fetchImpl}
          store={store}
          traceId={traceId}
          onTraceId={setTraceId}
        />
      </div>
    </div>
  )
}

function pane(active: boolean): string {
  return active ? 'flex min-h-0 flex-1 flex-col overflow-hidden' : 'hidden'
}
