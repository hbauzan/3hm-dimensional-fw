import { isRecord } from './json.ts'
import { fail, ok } from './result.ts'
import {
  FHV1_EVAL_GRANULARITIES,
  FHV1_FILTER_MODES,
  type Fhv1ChatTelemetry,
  type Fhv1EvalGranularity,
  type Fhv1FilterMode,
  type ParseResult,
} from './types.ts'

export const FHV1_ROGUE_INDICES = [292, 297, 308, 329, 386, 404, 577, 616, 780] as const

export const FHV1_TIER_NAMES = [
  'ZeroSpan',
  'LowAnchor',
  'Moderate',
  'HighVolatility',
  'ExtremeMovement',
] as const

export const FHV1_METRICS = ['variance', 'std_dev', 'span'] as const

export type Fhv1Metric = (typeof FHV1_METRICS)[number]

export interface Fhv1ProfileSummary {
  profile_id: string
  policy_id: string
  sample_count: number
  normalize: boolean
  use_rogue_mask_default: boolean
}

export interface Fhv1QuantileCutoffs {
  p25: number
  p75: number
  p90: number
}

export interface Fhv1ProfileDetail extends Fhv1ProfileSummary {
  min: number[]
  max: number[]
  mean: number[]
  span: number[]
  variance: number[]
  std_dev: number[]
  movement_tier_codes: number[]
  quantile_cutoffs: Fhv1QuantileCutoffs
}

export interface Fhv1LabChunk {
  chunk_index: number
  chunk_strategy: string
  chunk_passed: boolean
  failed_dims_count: number
  max_violation_delta: number
}

export interface Fhv1Evaluation {
  trace_id: string
  profile_id: string
  policy_id: string
  eval_granularity: Fhv1EvalGranularity
  use_rogue_mask: boolean
  overall_passed: boolean
  full_text_passed: boolean
  all_chunks_passed: boolean
  embedding_ms: number
  eval_latency_ns: number
  chunks: Fhv1LabChunk[]
}

export interface Fhv1TraceSummary {
  trace_id: string
  source_kind: string
  profile_id: string
  chunk_index: number
  overall_passed: boolean
  failed_dims_count: number
  max_violation_delta: number
}

export interface Fhv1TracePage {
  page: number
  page_size: number
  total: number
  rows: Fhv1TraceSummary[]
}

export function formatLosslessF64(value: number): string {
  return String(value)
}

export function writeExactText(text: string): Promise<void> {
  return navigator.clipboard.writeText(text)
}

export function isFhv1FilterMode(value: string): value is Fhv1FilterMode {
  return (FHV1_FILTER_MODES as readonly string[]).includes(value)
}

export function isFhv1EvalGranularity(value: string): value is Fhv1EvalGranularity {
  return (FHV1_EVAL_GRANULARITIES as readonly string[]).includes(value)
}

export function isFhv1Metric(value: string): value is Fhv1Metric {
  return (FHV1_METRICS as readonly string[]).includes(value)
}

export function isFhv1RogueDim(index: number): boolean {
  return (FHV1_ROGUE_INDICES as readonly number[]).includes(index)
}

export function movementTierName(code: number): string {
  return FHV1_TIER_NAMES[code] ?? `tier-${code}`
}

export function parseObservedBitsHex(value: unknown): ParseResult<string> {
  if (typeof value !== 'string' || !/^0x[0-9a-f]{16}$/.test(value)) {
    return fail('observed_bits_hex is not a 16-digit hex word')
  }
  return ok(value)
}

export function parseFhv1ChatTelemetry(value: unknown): ParseResult<Fhv1ChatTelemetry> {
  if (!isRecord(value)) return fail('fhv1 telemetry is missing')
  if (value.failing_tier !== 'FHV1_AABB_ENVELOPE') return fail('fhv1 failing_tier is not FHV1_AABB_ENVELOPE')
  const traceId = readString(value, 'trace_id')
  const profileId = readString(value, 'profile_id')
  const policyId = readString(value, 'policy_id')
  const granularity = readGranularity(value, 'eval_granularity')
  const useRogueMask = readBoolean(value, 'use_rogue_mask')
  const fullTextPassed = readBoolean(value, 'full_text_passed')
  const allChunksPassed = readBoolean(value, 'all_chunks_passed')
  const failingChunk = readCount(value, 'failing_chunk_index')
  const failedDims = readCount(value, 'failed_dims_count')
  const underflow = readCount(value, 'underflow_count')
  const overflow = readCount(value, 'overflow_count')
  const delta = readNumber(value, 'max_violation_delta')
  const embedding = readNumber(value, 'embedding_ms')
  const latency = readCount(value, 'eval_latency_ns')
  if (
    traceId === undefined ||
    profileId === undefined ||
    policyId === undefined ||
    granularity === undefined ||
    useRogueMask === undefined ||
    fullTextPassed === undefined ||
    allChunksPassed === undefined ||
    failingChunk === undefined ||
    failedDims === undefined ||
    underflow === undefined ||
    overflow === undefined ||
    delta === undefined ||
    embedding === undefined ||
    latency === undefined
  ) {
    return fail('fhv1 telemetry is incomplete')
  }
  return ok({
    trace_id: traceId,
    profile_id: profileId,
    policy_id: policyId,
    failing_tier: 'FHV1_AABB_ENVELOPE',
    eval_granularity: granularity,
    use_rogue_mask: useRogueMask,
    full_text_passed: fullTextPassed,
    all_chunks_passed: allChunksPassed,
    failing_chunk_index: failingChunk,
    failed_dims_count: failedDims,
    underflow_count: underflow,
    overflow_count: overflow,
    max_violation_delta: delta,
    embedding_ms: embedding,
    eval_latency_ns: latency,
  })
}

export function parseFhv1ProfileSummary(value: unknown): ParseResult<Fhv1ProfileSummary> {
  if (!isRecord(value)) return fail('fhv1 profile is not an object')
  const profileId = readString(value, 'profile_id')
  const policyId = readString(value, 'policy_id')
  const sampleCount = readCount(value, 'sample_count')
  const normalize = readBoolean(value, 'normalize')
  const mask = readBoolean(value, 'use_rogue_mask_default')
  if (
    profileId === undefined ||
    policyId === undefined ||
    sampleCount === undefined ||
    normalize === undefined ||
    mask === undefined
  ) {
    return fail('fhv1 profile summary is incomplete')
  }
  return ok({
    profile_id: profileId,
    policy_id: policyId,
    sample_count: sampleCount,
    normalize,
    use_rogue_mask_default: mask,
  })
}

export function parseFhv1Profiles(value: unknown): ParseResult<Fhv1ProfileSummary[]> {
  if (!Array.isArray(value)) return fail('fhv1 profiles payload is not an array')
  const profiles: Fhv1ProfileSummary[] = []
  for (const entry of value) {
    const parsed = parseFhv1ProfileSummary(entry)
    if (!parsed.ok) return parsed
    profiles.push(parsed.value)
  }
  return ok(profiles)
}

export function parseFhv1ProfileDetail(value: unknown): ParseResult<Fhv1ProfileDetail> {
  const summary = parseFhv1ProfileSummary(value)
  if (!summary.ok) return summary
  if (!isRecord(value)) return fail('fhv1 profile detail is not an object')
  const min = readNumberArray(value, 'min')
  const max = readNumberArray(value, 'max')
  const mean = readNumberArray(value, 'mean')
  const span = readNumberArray(value, 'span')
  const variance = readNumberArray(value, 'variance')
  const stdDev = readNumberArray(value, 'std_dev')
  const tiers = readCountArray(value, 'movement_tier_codes')
  const cutoffs = readCutoffs(value.quantile_cutoffs)
  const width = min?.length
  if (
    min === undefined ||
    max === undefined ||
    mean === undefined ||
    span === undefined ||
    variance === undefined ||
    stdDev === undefined ||
    tiers === undefined ||
    cutoffs === undefined ||
    width === undefined ||
    max.length !== width ||
    mean.length !== width ||
    span.length !== width ||
    variance.length !== width ||
    stdDev.length !== width ||
    tiers.length !== width
  ) {
    return fail('fhv1 profile detail is incomplete')
  }
  return ok({
    ...summary.value,
    min,
    max,
    mean,
    span,
    variance,
    std_dev: stdDev,
    movement_tier_codes: tiers,
    quantile_cutoffs: cutoffs,
  })
}

export function parseFhv1Evaluation(value: unknown): ParseResult<Fhv1Evaluation> {
  if (!isRecord(value)) return fail('fhv1 evaluation is not an object')
  const traceId = readString(value, 'trace_id')
  const profileId = readString(value, 'profile_id')
  const policyId = readString(value, 'policy_id')
  const granularity = readGranularity(value, 'eval_granularity')
  const useRogueMask = readBoolean(value, 'use_rogue_mask')
  const overall = readBoolean(value, 'overall_passed')
  const fullText = readBoolean(value, 'full_text_passed')
  const allChunks = readBoolean(value, 'all_chunks_passed')
  const embedding = readNumber(value, 'embedding_ms')
  const latency = readCount(value, 'eval_latency_ns')
  const chunks = parseChunks(value.chunks)
  if (
    traceId === undefined ||
    profileId === undefined ||
    policyId === undefined ||
    granularity === undefined ||
    useRogueMask === undefined ||
    overall === undefined ||
    fullText === undefined ||
    allChunks === undefined ||
    embedding === undefined ||
    latency === undefined ||
    !chunks.ok
  ) {
    return chunks.ok ? fail('fhv1 evaluation is incomplete') : chunks
  }
  return ok({
    trace_id: traceId,
    profile_id: profileId,
    policy_id: policyId,
    eval_granularity: granularity,
    use_rogue_mask: useRogueMask,
    overall_passed: overall,
    full_text_passed: fullText,
    all_chunks_passed: allChunks,
    embedding_ms: embedding,
    eval_latency_ns: latency,
    chunks: chunks.value,
  })
}

export function parseFhv1TracePage(value: unknown): ParseResult<Fhv1TracePage> {
  if (!isRecord(value)) return fail('fhv1 trace page is not an object')
  const page = readCount(value, 'page')
  const pageSize = readCount(value, 'page_size')
  const total = readCount(value, 'total')
  if (page === undefined || pageSize === undefined || total === undefined) {
    return fail('fhv1 trace page is incomplete')
  }
  if (!Array.isArray(value.rows)) return fail('fhv1 trace rows are missing')
  const rows: Fhv1TraceSummary[] = []
  for (const entry of value.rows) {
    if (!isRecord(entry)) return fail('fhv1 trace row is not an object')
    const traceId = readString(entry, 'trace_id')
    const sourceKind = readString(entry, 'source_kind')
    const profileId = readString(entry, 'profile_id')
    const chunkIndex = readCount(entry, 'chunk_index')
    const overall = readBoolean(entry, 'overall_passed')
    const failed = readCount(entry, 'failed_dims_count')
    const delta = readNumber(entry, 'max_violation_delta')
    if (
      traceId === undefined ||
      sourceKind === undefined ||
      profileId === undefined ||
      chunkIndex === undefined ||
      overall === undefined ||
      failed === undefined ||
      delta === undefined
    ) {
      return fail('fhv1 trace row is incomplete')
    }
    rows.push({
      trace_id: traceId,
      source_kind: sourceKind,
      profile_id: profileId,
      chunk_index: chunkIndex,
      overall_passed: overall,
      failed_dims_count: failed,
      max_violation_delta: delta,
    })
  }
  return ok({ page, page_size: pageSize, total, rows })
}

function parseChunks(value: unknown): ParseResult<Fhv1LabChunk[]> {
  if (!Array.isArray(value)) return fail('fhv1 chunks are missing')
  const chunks: Fhv1LabChunk[] = []
  for (const entry of value) {
    if (!isRecord(entry)) return fail('fhv1 chunk is not an object')
    const index = readCount(entry, 'chunk_index')
    const strategy = readString(entry, 'chunk_strategy')
    const passed = readBoolean(entry, 'chunk_passed')
    const failed = readCount(entry, 'failed_dims_count')
    const delta = readNumber(entry, 'max_violation_delta')
    if (
      index === undefined ||
      strategy === undefined ||
      passed === undefined ||
      failed === undefined ||
      delta === undefined
    ) {
      return fail('fhv1 chunk is incomplete')
    }
    chunks.push({
      chunk_index: index,
      chunk_strategy: strategy,
      chunk_passed: passed,
      failed_dims_count: failed,
      max_violation_delta: delta,
    })
  }
  return ok(chunks)
}

function readNumberArray(record: Record<string, unknown>, key: string): number[] | undefined {
  const value = record[key]
  if (!Array.isArray(value)) return undefined
  const numbers: number[] = []
  for (const entry of value) {
    if (typeof entry !== 'number' || !Number.isFinite(entry)) return undefined
    numbers.push(entry)
  }
  return numbers
}

function readCountArray(record: Record<string, unknown>, key: string): number[] | undefined {
  const value = record[key]
  if (!Array.isArray(value)) return undefined
  const numbers: number[] = []
  for (const entry of value) {
    if (typeof entry !== 'number' || !Number.isInteger(entry) || entry < 0) return undefined
    numbers.push(entry)
  }
  return numbers
}

function readCutoffs(value: unknown): Fhv1QuantileCutoffs | undefined {
  if (!isRecord(value)) return undefined
  const p25 = readNumber(value, 'p25')
  const p75 = readNumber(value, 'p75')
  const p90 = readNumber(value, 'p90')
  if (p25 === undefined || p75 === undefined || p90 === undefined) return undefined
  return { p25, p75, p90 }
}

function readString(record: Record<string, unknown>, key: string): string | undefined {
  const value = record[key]
  return typeof value === 'string' ? value : undefined
}

function readBoolean(record: Record<string, unknown>, key: string): boolean | undefined {
  const value = record[key]
  return typeof value === 'boolean' ? value : undefined
}

function readNumber(record: Record<string, unknown>, key: string): number | undefined {
  const value = record[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function readCount(record: Record<string, unknown>, key: string): number | undefined {
  const value = readNumber(record, key)
  return value !== undefined && Number.isInteger(value) && value >= 0 ? value : undefined
}

function readGranularity(
  record: Record<string, unknown>,
  key: string,
): Fhv1EvalGranularity | undefined {
  const value = readString(record, key)
  return value !== undefined && isFhv1EvalGranularity(value) ? value : undefined
}
