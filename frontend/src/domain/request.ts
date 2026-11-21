import { normalizeOverrides } from './overrides.ts'
import type {
  ChatDraft,
  ChatMessage,
  ChatOverrideBody,
  ChatRequest,
  ChatUpstreamBody,
  UpstreamSelection,
} from './types.ts'

export function buildChatRequest(draft: ChatDraft): ChatRequest {
  const request: ChatRequest = {
    messages: draft.messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
    upstream: upstreamBody(draft.upstream),
  }
  const domainId = draft.domainId.trim()
  if (domainId) request.domain_id = domainId
  if (draft.overridesArmed) request.overrides = overrideBody(draft)
  const mode = draft.filterMode ?? '3hm_default'
  if (mode !== '3hm_default') {
    request.filter_mode = mode
    const profileId = draft.fhv1ProfileId?.trim() ?? ''
    if (profileId) request.fhv1_profile_id = profileId
    if (draft.fhv1Granularity) request.fhv1_granularity = draft.fhv1Granularity
    if (typeof draft.fhv1UseRogueMask === 'boolean') {
      request.fhv1_use_rogue_mask = draft.fhv1UseRogueMask
    }
  }
  return request
}

function overrideBody(draft: ChatDraft): ChatOverrideBody {
  const normalized = normalizeOverrides(draft.overrides)
  const body: ChatOverrideBody = {
    l1_threshold: normalized.l1_threshold,
    l2_threshold: normalized.l2_threshold,
    quorum_k: normalized.quorum_k,
  }
  if (draft.epsilonPinned) body.epsilon = normalized.epsilon
  return body
}

export function hasUserText(messages: readonly ChatMessage[]): boolean {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]
    if (message?.role === 'user' && message.content.trim()) return true
  }
  return false
}

function upstreamBody(selection: UpstreamSelection): ChatUpstreamBody {
  const body: ChatUpstreamBody = { provider: selection.provider }
  const model = selection.model.trim()
  const baseUrl = selection.baseUrl.trim()
  const apiKey = selection.apiKey.trim()
  if (model) body.model = model
  if (baseUrl) body.base_url = baseUrl
  if (apiKey) body.api_key = apiKey
  if (selection.useEnv) body.use_env = true
  return body
}
