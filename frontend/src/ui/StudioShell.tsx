import type { SessionStore } from '../domain/session.ts'
import { Playground } from './Playground.tsx'

export function StudioShell({
  fetchImpl,
  store,
}: {
  fetchImpl?: typeof fetch
  store?: SessionStore
}) {
  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-studio-bg text-studio-text">
      <Playground fetchImpl={fetchImpl} store={store} fill />
    </div>
  )
}
