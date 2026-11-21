import { isFhv1EvalGranularity, isFhv1FilterMode } from './fhv1.ts'
import { readStoredFloat, readStoredInt } from './overrides.ts'
import { isUpstreamProvider, PROVIDER_DEFAULTS } from './presets.ts'
import type {
  Fhv1EvalGranularity,
  Fhv1FilterMode,
  SpaSession,
  UpstreamProvider,
  UpstreamSelection,
} from './types.ts'

const GATEWAY = 'sf.spa.gatewayBase'
const DOMAIN = 'sf.spa.domainId'
const ARMED = 'sf.spa.overridesArmed'

export const DEFAULT_OVERRIDES_ARMED = false
const L1 = 'sf.spa.l1'
const L2 = 'sf.spa.l2'
const QUORUM = 'sf.spa.quorumK'
const EPSILON = 'sf.spa.epsilon'
const EPSILON_PINNED = 'sf.spa.epsilonPinned'
const PROVIDER = 'sf.spa.provider'

const USE_ENV = 'sf.spa.useEnv'
const FILTER = 'sf.spa.filterMode'
const FHV1_PROFILE = 'sf.spa.fhv1ProfileId'
const FHV1_GRANULARITY = 'sf.spa.fhv1Granularity'
const FHV1_MASK = 'sf.spa.fhv1UseRogueMask'

export interface SessionStore {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export interface MemorySessionStore extends SessionStore {
  snapshot(): Record<string, string>
}

export function defaultGatewayBase(): string {
  const fromEnv = import.meta.env.VITE_SF_GATEWAY_URL
  if (typeof fromEnv === 'string' && fromEnv.trim()) return fromEnv.trim()
  return 'http://127.0.0.1:8088'
}

export function apiKeyStorageKey(provider: UpstreamProvider): string {
  return `sf.spa.upstream.${provider}.apiKey`
}

export function memorySessionStore(seed: Record<string, string> = {}): MemorySessionStore {
  const data = new Map(Object.entries(seed))
  return {
    getItem(key) {
      return data.get(key) ?? null
    },
    setItem(key, value) {
      data.set(key, value)
    },
    removeItem(key) {
      data.delete(key)
    },
    snapshot() {
      return Object.fromEntries(data)
    },
  }
}

export function browserSessionStore(): SessionStore {
  return {
    getItem(key) {
      try {
        return window.localStorage.getItem(key)
      } catch {
        return null
      }
    },
    setItem(key, value) {
      try {
        window.localStorage.setItem(key, value)
      } catch {
        // Private mode still sends the key on the POST body.
      }
    },
    removeItem(key) {
      try {
        window.localStorage.removeItem(key)
      } catch {
        // Private mode has nothing stored to drop.
      }
    },
  }
}

export function loadProviderUpstream(
  provider: UpstreamProvider,
  store: SessionStore,
): UpstreamSelection {
  const defaults = PROVIDER_DEFAULTS[provider]
  const useEnv = store.getItem(USE_ENV) === '1'
  return {
    provider,
    baseUrl: store.getItem(baseUrlKey(provider)) ?? defaults.baseUrl,
    model: store.getItem(modelKey(provider)) ?? defaults.model,
    apiKey: store.getItem(apiKeyStorageKey(provider)) ?? '',
    useEnv,
  }
}

export function loadSession(store: SessionStore): SpaSession {
  const storedProvider = store.getItem(PROVIDER)?.trim() ?? ''
  const provider = isUpstreamProvider(storedProvider) ? storedProvider : 'mock'
  const gateway = store.getItem(GATEWAY)?.trim()
  const domain = store.getItem(DOMAIN)
  const armed = store.getItem(ARMED)
  return {
    gatewayBase: gateway ? gateway : defaultGatewayBase(),
    domainId: domain === null ? 'python' : domain,
    overridesArmed: armed === null ? DEFAULT_OVERRIDES_ARMED : armed === '1',
    epsilonPinned: store.getItem(EPSILON_PINNED) === '1',
    overrides: {
      l1_threshold: readStoredFloat(store.getItem(L1), 0.5, 0, 1, 2),
      l2_threshold: readStoredFloat(store.getItem(L2), 0.5, 0, 1, 2),
      quorum_k: readStoredInt(store.getItem(QUORUM), 103, 1, 1015),
      epsilon: readStoredFloat(store.getItem(EPSILON), 0, 0, 0.5, 3),
    },
    upstream: loadProviderUpstream(provider, store),
    filterMode: readFilterMode(store.getItem(FILTER)),
    fhv1ProfileId: store.getItem(FHV1_PROFILE) ?? '',
    fhv1Granularity: readGranularity(store.getItem(FHV1_GRANULARITY)),
    fhv1UseRogueMask: store.getItem(FHV1_MASK) === '1',
  }
}

export function saveSession(store: SessionStore, session: SpaSession): void {
  store.setItem(GATEWAY, session.gatewayBase)
  store.setItem(DOMAIN, session.domainId)
  store.setItem(ARMED, session.overridesArmed ? '1' : '0')
  store.setItem(L1, String(session.overrides.l1_threshold))
  store.setItem(L2, String(session.overrides.l2_threshold))
  store.setItem(QUORUM, String(session.overrides.quorum_k))
  store.setItem(EPSILON, String(session.overrides.epsilon))
  store.setItem(EPSILON_PINNED, session.epsilonPinned ? '1' : '0')
  store.setItem(PROVIDER, session.upstream.provider)
  store.setItem(USE_ENV, session.upstream.useEnv ? '1' : '0')
  store.setItem(baseUrlKey(session.upstream.provider), session.upstream.baseUrl)
  store.setItem(modelKey(session.upstream.provider), session.upstream.model)
  const secretKey = apiKeyStorageKey(session.upstream.provider)
  if (session.upstream.apiKey) store.setItem(secretKey, session.upstream.apiKey)
  else store.removeItem(secretKey)
  store.setItem(FILTER, session.filterMode ?? '3hm_default')
  store.setItem(FHV1_PROFILE, session.fhv1ProfileId ?? '')
  store.setItem(FHV1_GRANULARITY, session.fhv1Granularity ?? 'clauses')
  store.setItem(FHV1_MASK, session.fhv1UseRogueMask ? '1' : '0')
}

function readFilterMode(value: string | null): Fhv1FilterMode {
  return value !== null && isFhv1FilterMode(value) ? value : '3hm_default'
}

function readGranularity(value: string | null): Fhv1EvalGranularity {
  return value !== null && isFhv1EvalGranularity(value) ? value : 'clauses'
}

function baseUrlKey(provider: UpstreamProvider): string {
  return `sf.spa.upstream.${provider}.baseUrl`
}

function modelKey(provider: UpstreamProvider): string {
  return `sf.spa.upstream.${provider}.model`
}
