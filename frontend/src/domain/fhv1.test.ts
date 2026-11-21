import { describe, expect, it } from 'vitest'
import { parseChatBreach } from './breach.ts'
import {
  formatLosslessF64,
  parseFhv1Evaluation,
  parseObservedBitsHex,
} from './fhv1.ts'
import { buildChatRequest } from './request.ts'
import { loadSession, memorySessionStore, saveSession } from './session.ts'
import type { ChatDraft, SpaSession } from './types.ts'

function draft(patch: Partial<ChatDraft> = {}): ChatDraft {
  return {
    messages: [{ role: 'user', content: 'hola' }],
    domainId: 'python',
    overridesArmed: true,
    overrides: {
      l1_threshold: 0.5,
      l2_threshold: 0.5,
      quorum_k: 103,
      epsilon: 0,
    },
    upstream: {
      provider: 'mock',
      baseUrl: '',
      model: 'mock',
      apiKey: '',
    },
    ...patch,
  }
}

const telemetry = {
  trace_id: 'chat-1',
  profile_id: 'python-v1-abc',
  policy_id: 'python',
  failing_tier: 'FHV1_AABB_ENVELOPE',
  eval_granularity: 'clauses',
  use_rogue_mask: false,
  full_text_passed: false,
  all_chunks_passed: false,
  failing_chunk_index: 0,
  failed_dims_count: 1,
  underflow_count: 0,
  overflow_count: 1,
  max_violation_delta: 0.1,
  embedding_ms: 0.1,
  eval_latency_ns: 7,
}

describe('fhv1 lossless formatting', () => {
  it('prints the IEEE value with String and keeps a 64-bit hex word', () => {
    expect(formatLosslessF64(0.1)).toBe('0.1')
    expect(formatLosslessF64(0.30000000000000004)).toBe('0.30000000000000004')
    expect(formatLosslessF64(0.1)).not.toBe('0.1000')
    expect(parseObservedBitsHex('0x3fc0000000000000')).toEqual({
      ok: true,
      value: '0x3fc0000000000000',
    })
    expect(parseObservedBitsHex('0x3fc000000000000').ok).toBe(false)
  })

  it('omits filter fields for the default mode and sends them for fhv1 modes', () => {
    expect(buildChatRequest(draft())).not.toHaveProperty('filter_mode')
    expect(buildChatRequest(draft({ filterMode: '3hm_default' }))).not.toHaveProperty('filter_mode')
    expect(
      buildChatRequest(
        draft({
          filterMode: 'fhv1',
          fhv1ProfileId: ' python-v1-abc ',
          fhv1Granularity: 'full_only',
          fhv1UseRogueMask: false,
        }),
      ),
    ).toMatchObject({
      filter_mode: 'fhv1',
      fhv1_profile_id: 'python-v1-abc',
      fhv1_granularity: 'full_only',
      fhv1_use_rogue_mask: false,
    })
    expect(
      buildChatRequest(
        draft({
          filterMode: '3hm_plus_fhv1',
          fhv1ProfileId: 'python-v1-abc',
          fhv1Granularity: 'clauses',
          fhv1UseRogueMask: true,
        }),
      ).filter_mode,
    ).toBe('3hm_plus_fhv1')
  })

  it('maps an fhv1 ingress breach without rounding the delta', () => {
    const parsed = parseChatBreach({
      error: {
        kind: 'fhv1_ingress_breach',
        code: 'SEMANTIC_CONTAINMENT_BREACH',
        message: 'fhv1 AABB envelope rejected the prompt',
        telemetry,
      },
    })
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) return
    expect(parsed.value.failing_tier).toBe('FHV1_AABB_ENVELOPE')
    expect(parsed.value.fhv1?.max_violation_delta).toBe(0.1)
    expect(formatLosslessF64(parsed.value.fhv1?.max_violation_delta ?? Number.NaN)).toBe('0.1')
  })

  it('keeps evaluation deltas as raw numbers', () => {
    const parsed = parseFhv1Evaluation({
      trace_id: 'lab-1',
      profile_id: 'python-v1-abc',
      policy_id: 'python',
      eval_granularity: 'clauses',
      use_rogue_mask: false,
      overall_passed: false,
      full_text_passed: false,
      all_chunks_passed: false,
      embedding_ms: 0.1,
      eval_latency_ns: 7,
      chunks: [
        {
          chunk_index: 0,
          chunk_strategy: 'full_doc',
          chunk_passed: false,
          failed_dims_count: 1,
          max_violation_delta: 0.30000000000000004,
        },
      ],
    })
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) return
    expect(parsed.value.chunks[0]?.max_violation_delta).toBe(0.30000000000000004)
  })

  it('round-trips the filter selection and falls back when the stored mode is unknown', () => {
    const store = memorySessionStore()
    const session: SpaSession = {
      gatewayBase: 'http://127.0.0.1:8088',
      domainId: 'python',
      overridesArmed: false,
      overrides: { l1_threshold: 0.5, l2_threshold: 0.5, quorum_k: 103, epsilon: 0 },
      upstream: { provider: 'mock', baseUrl: '', model: 'mock', apiKey: '' },
      filterMode: 'fhv1',
      fhv1ProfileId: 'python-v1-abc',
      fhv1Granularity: 'full_mirror',
      fhv1UseRogueMask: true,
    }
    saveSession(store, session)
    expect(loadSession(store)).toMatchObject({
      filterMode: 'fhv1',
      fhv1ProfileId: 'python-v1-abc',
      fhv1Granularity: 'full_mirror',
      fhv1UseRogueMask: true,
    })
    store.setItem('sf.spa.filterMode', 'nope')
    expect(loadSession(store).filterMode).toBe('3hm_default')
  })
})
