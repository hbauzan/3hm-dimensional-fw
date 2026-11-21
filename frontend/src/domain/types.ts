export const FAILING_TIERS = [
  'L1_CENTROID_COSINE',
  'L2_CLAUSE_GATE',
  'L3_SPECTRAL_QUORUM',
  'L3_PAIRWISE_QUORUM',
  'FHV1_AABB_ENVELOPE',
] as const

export const FHV1_FILTER_MODES = ['3hm_default', 'fhv1', '3hm_plus_fhv1'] as const

export type Fhv1FilterMode = (typeof FHV1_FILTER_MODES)[number]

export const FHV1_EVAL_GRANULARITIES = ['full_only', 'clauses', 'full_mirror'] as const

export type Fhv1EvalGranularity = (typeof FHV1_EVAL_GRANULARITIES)[number]

export interface Fhv1ChatTelemetry {
  trace_id: string
  profile_id: string
  policy_id: string
  failing_tier: 'FHV1_AABB_ENVELOPE'
  eval_granularity: Fhv1EvalGranularity
  use_rogue_mask: boolean
  full_text_passed: boolean
  all_chunks_passed: boolean
  failing_chunk_index: number
  failed_dims_count: number
  underflow_count: number
  overflow_count: number
  max_violation_delta: number
  embedding_ms: number
  eval_latency_ns: number
}

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
  filter_mode?: Fhv1FilterMode
  fhv1_profile_id?: string
  fhv1_granularity?: Fhv1EvalGranularity
  fhv1_use_rogue_mask?: boolean
}

export interface ChatDraft {
  messages: readonly ChatMessage[]
  domainId: string
  overridesArmed: boolean
  /** When false or omitted, the request leaves the stored dilation untouched. */
  epsilonPinned?: boolean
  overrides: ChatOverrides
  upstream: UpstreamSelection
  filterMode?: Fhv1FilterMode
  fhv1ProfileId?: string
  fhv1Granularity?: Fhv1EvalGranularity
  fhv1UseRogueMask?: boolean
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
  fhv1?: Fhv1ChatTelemetry
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
  filterMode?: Fhv1FilterMode
  fhv1ProfileId?: string
  fhv1Granularity?: Fhv1EvalGranularity
  fhv1UseRogueMask?: boolean
}

export type ChatOutcome =
  | { kind: 'pass'; text: string; telemetry?: ChatTelemetryDto }
  | { kind: 'breach'; breach: ChatBreachDto }
  | { kind: 'error'; status: number; message: string }
