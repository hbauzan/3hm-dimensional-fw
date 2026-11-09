export const FAILING_TIERS = [
  'L1_CENTROID_COSINE',
  'L2_CLAUSE_GATE',
  'L3_SPECTRAL_QUORUM',
  'L3_PAIRWISE_QUORUM',
] as const

export type FailingTier = (typeof FAILING_TIERS)[number]

export type ChatRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  role: ChatRole
  content: string
}

export interface ChatOverrides {
  l1_threshold: number
  l2_threshold: number
  quorum_k: number
  epsilon: number
}

export const UPSTREAM_PROVIDERS = [
  'mock',
  'gemini',
  'openai',
  'deepseek',
  'groq',
  'ollama',
] as const

export type UpstreamProvider = (typeof UPSTREAM_PROVIDERS)[number]

export interface UpstreamSelection {
  provider: UpstreamProvider
  baseUrl: string
  model: string
  apiKey: string
  useEnv?: boolean
}

export interface ChatUpstreamBody {
  provider: UpstreamProvider
  model?: string
  base_url?: string
  api_key?: string
  use_env?: boolean
}

export interface ProviderEnvDto {
  provider: string
  configured: boolean
  api_key: string
  base_url: string
  model: string
  env_key_found?: string | null
}

export interface UpstreamEnvCatalogDto {
  use_env_available: boolean
  providers: Record<string, ProviderEnvDto>
}

export interface ChatOverrideBody {
  l1_threshold: number
  l2_threshold: number
  quorum_k: number
  epsilon?: number
}

export interface ChatRequest {
  messages: ChatMessage[]
  domain_id?: string
  overrides?: ChatOverrideBody
  upstream: ChatUpstreamBody
}

export interface ChatDraft {
  messages: readonly ChatMessage[]
  domainId: string
  overridesArmed: boolean
  /** When false or omitted, the request leaves the stored dilation untouched. */
  epsilonPinned?: boolean
  overrides: ChatOverrides
  upstream: UpstreamSelection
}

export interface Tier1Breach {
  passed: boolean
  cosine: number
  threshold: number
}

export interface Tier2Breach {
  passed: boolean
  threshold: number
  breached_clause_index?: number
  breached_clause_text?: string
  clause_cosine?: number
}

export interface Tier3Breach {
  evaluated: boolean
  passed?: boolean
  affirmative_votes?: number
  required_votes?: number
}

export interface ChatTelemetryDto {
  decision: 'BREACH' | 'PASS'
  failing_tier?: FailingTier | string
  l1: Tier1Breach
  l2: Tier2Breach
  l3: Tier3Breach
  clauses_skipped?: number
  normalizer_segmenter_us?: number
  embedding_inference_ms?: number
  simd_gate_kernel_us?: number
  total_pipeline_ms?: number
}

export type ChatBreachDto = ChatTelemetryDto & {
  decision: 'BREACH'
  failing_tier: FailingTier
}

export type ParseResult<T> = { ok: true; value: T } | { ok: false; message: string }

export interface SpaSession {
  gatewayBase: string
  domainId: string
  overridesArmed: boolean
  /** When false or omitted, live tuning does not post `epsilon`. */
  epsilonPinned?: boolean
  overrides: ChatOverrides
  upstream: UpstreamSelection
}

export type ChatOutcome =
  | { kind: 'pass'; text: string; telemetry?: ChatTelemetryDto }
  | { kind: 'breach'; breach: ChatBreachDto }
  | { kind: 'error'; status: number; message: string }
