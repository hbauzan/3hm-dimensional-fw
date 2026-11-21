import { resolveChatEndpoint } from '../domain/endpoint.ts'
import {
  parseFhv1Evaluation,
  parseFhv1Profiles,
  parseFhv1TracePage,
  type Fhv1Evaluation,
  type Fhv1ProfileSummary,
  type Fhv1TracePage,
} from '../domain/fhv1.ts'
import { isRecord } from '../domain/json.ts'
import type { Fhv1EvalGranularity, ParseResult } from '../domain/types.ts'
import { fail, ok } from '../domain/result.ts'

export interface Fhv1EvaluateRequest {
  profileId: string
  text: string
  granularity: Fhv1EvalGranularity
  useRogueMask: boolean
}

export interface Fhv1TraceListQuery {
  profileId?: string
  sourceKind?: string
  page?: number
  pageSize?: number
}

export async function listFhv1Profiles(
  gatewayBase: string,
  fetchImpl?: typeof fetch,
): Promise<ParseResult<Fhv1ProfileSummary[]>> {
  const loaded = await getJson(gatewayBase, '/api/v1/fhv1/profiles', fetchImpl)
  if (!loaded.ok) return loaded
  return parseFhv1Profiles(loaded.value)
}

export async function postFhv1Evaluate(
  gatewayBase: string,
  request: Fhv1EvaluateRequest,
  fetchImpl?: typeof fetch,
): Promise<ParseResult<Fhv1Evaluation>> {
  const loaded = await sendJson(
    gatewayBase,
    '/api/v1/fhv1/evaluate',
    {
      profile_id: request.profileId,
      text: request.text,
      eval_granularity: request.granularity,
      use_rogue_mask: request.useRogueMask,
    },
    fetchImpl,
  )
  if (!loaded.ok) return loaded
  return parseFhv1Evaluation(loaded.value)
}

export async function listFhv1Traces(
  gatewayBase: string,
  query: Fhv1TraceListQuery,
  fetchImpl?: typeof fetch,
): Promise<ParseResult<Fhv1TracePage>> {
  const params = new URLSearchParams()
  params.set('page', String(query.page ?? 1))
  params.set('page_size', String(query.pageSize ?? 20))
  if (query.profileId) params.set('profile_id', query.profileId)
  if (query.sourceKind) params.set('source_kind', query.sourceKind)
  const loaded = await getJson(gatewayBase, `/api/v1/fhv1/traces?${params.toString()}`, fetchImpl)
  if (!loaded.ok) return loaded
  return parseFhv1TracePage(loaded.value)
}

async function getJson(
  gatewayBase: string,
  path: string,
  fetchImpl?: typeof fetch,
): Promise<ParseResult<unknown>> {
  const url = resolveFhv1Url(gatewayBase, path)
  if (!url.ok) return url
  const fetchFn = fetchImpl ?? globalThis.fetch
  try {
    const response = await fetchFn(url.value)
    const payload = await readUnknown(response)
    if (!response.ok) return fail(explain(payload))
    return ok(payload)
  } catch (error) {
    return fail(error instanceof Error ? error.message : 'fhv1 request failed')
  }
}

async function sendJson(
  gatewayBase: string,
  path: string,
  body: unknown,
  fetchImpl?: typeof fetch,
): Promise<ParseResult<unknown>> {
  const url = resolveFhv1Url(gatewayBase, path)
  if (!url.ok) return url
  const fetchFn = fetchImpl ?? globalThis.fetch
  try {
    const response = await fetchFn(url.value, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
    const payload = await readUnknown(response)
    if (!response.ok) return fail(explain(payload))
    return ok(payload)
  } catch (error) {
    return fail(error instanceof Error ? error.message : 'fhv1 request failed')
  }
}

function resolveFhv1Url(gatewayBase: string, path: string): ParseResult<string> {
  const endpoint = resolveChatEndpoint(gatewayBase)
  if (!endpoint.ok) return endpoint
  const root = endpoint.value.replace(/\/api\/v1\/chat$/, '')
  return ok(`${root}${path}`)
}

async function readUnknown(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

function explain(payload: unknown): string {
  if (typeof payload === 'string' && payload.trim()) return payload.trim()
  if (isRecord(payload)) {
    const error = payload.error
    if (typeof error === 'string' && error.trim()) return error.trim()
    if (isRecord(error) && typeof error.message === 'string' && error.message.trim()) {
      return error.message.trim()
    }
  }
  if (payload === null) return 'empty fhv1 error body'
  return JSON.stringify(payload)
}
