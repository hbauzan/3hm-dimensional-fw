import type { EChartsCoreOption } from 'echarts/core'
import {
  formatLosslessF64,
  isFhv1RogueDim,
  movementTierName,
  type Fhv1Metric,
  type Fhv1ProfileDetail,
} from '../domain/fhv1.ts'

const AXIS = '#94a3b8'
const ACCENT = '#38bdf8'
const PASS = '#10b981'
const WARN = '#f59e0b'

export function envelopeTooltip(detail: Fhv1ProfileDetail, params: unknown): string {
  const dim = pointIndex(params)
  if (dim === undefined) return ''
  const min = detail.min[dim]
  const max = detail.max[dim]
  const mean = detail.mean[dim]
  if (min === undefined || max === undefined || mean === undefined) return ''
  return [
    `dim ${dim}`,
    `min ${formatLosslessF64(min)}`,
    `max ${formatLosslessF64(max)}`,
    `mean ${formatLosslessF64(mean)}`,
  ].join('\n')
}

export function envelopeOption(detail: Fhv1ProfileDetail): EChartsCoreOption {
  const dims = detail.min.map((_, index) => index)
  const band = detail.max.map((value, index) => value - (detail.min[index] ?? 0))
  return {
    textStyle: { color: AXIS },
    tooltip: { trigger: 'axis', formatter: (params: unknown) => envelopeTooltip(detail, params) },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: dims, axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS }, scale: true },
    series: [
      {
        name: 'min',
        type: 'line',
        data: detail.min,
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      {
        name: 'envelope',
        type: 'line',
        data: band,
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: ACCENT, opacity: 0.25 },
      },
      { name: 'mean', type: 'line', data: detail.mean, symbol: 'none', lineStyle: { color: PASS } },
    ],
  }
}

export function rankingOption(detail: Fhv1ProfileDetail, metric: Fhv1Metric): EChartsCoreOption {
  const values = metricValues(detail, metric)
  const rogue = values.map((value, index) => (isFhv1RogueDim(index) ? value : null))
  return {
    textStyle: { color: AXIS },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const dim = pointIndex(params)
        if (dim === undefined) return ''
        const value = values[dim]
        return value === undefined ? '' : `dim ${dim} ${metric} ${formatLosslessF64(value)}`
      },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: values.map((_, index) => index), axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS }, scale: true },
    series: [
      { name: metric, type: 'bar', data: values, itemStyle: { color: ACCENT } },
      { name: 'rogue', type: 'scatter', data: rogue, itemStyle: { color: WARN }, symbol: 'diamond' },
    ],
  }
}

export function attributionOption(
  counts: readonly number[],
  oobCatch: readonly number[] | null = null,
): EChartsCoreOption {
  const width = Math.max(counts.length, oobCatch?.length ?? 0)
  const axis = Array.from({ length: width }, (_, index) => index)
  const rogue = axis.map((index) =>
    isFhv1RogueDim(index) && counts[index] !== undefined ? counts[index] : null,
  )
  const inDomain = {
    name: 'in_domain_fail',
    type: 'bar',
    data: axis.map((index) => counts[index] ?? null),
    itemStyle: { color: ACCENT },
  }
  const caught = {
    name: 'oob_catch',
    type: 'bar',
    data: axis.map((index) => oobCatch?.[index] ?? null),
    itemStyle: { color: PASS },
  }
  const rogueSeries = {
    name: 'rogue',
    type: 'scatter',
    data: rogue,
    itemStyle: { color: WARN },
    symbol: 'diamond',
  }
  return {
    textStyle: { color: AXIS },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const dim = pointIndex(params)
        if (dim === undefined) return ''
        const lines = [`dim ${dim}`]
        const inDomainValue = counts[dim]
        if (inDomainValue !== undefined) lines.push(`in_domain_fail ${formatLosslessF64(inDomainValue)}`)
        const caughtValue = oobCatch?.[dim]
        if (caughtValue !== undefined) lines.push(`oob_catch ${formatLosslessF64(caughtValue)}`)
        return lines.join('\n')
      },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: axis, axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS } },
    series: oobCatch ? [inDomain, caught, rogueSeries] : [inDomain, rogueSeries],
  }
}

export function tierOption(detail: Fhv1ProfileDetail): EChartsCoreOption {
  const counts = [0, 0, 0, 0, 0]
  for (const code of detail.movement_tier_codes) {
    const current = counts[code]
    if (current !== undefined) counts[code] = current + 1
  }
  return {
    textStyle: { color: AXIS },
    xAxis: {
      type: 'category',
      data: counts.map((_, index) => movementTierName(index)),
      axisLabel: { color: AXIS, rotate: 30 },
    },
    yAxis: { type: 'value', axisLabel: { color: AXIS } },
    series: [{ name: 'tiers', type: 'bar', data: counts, itemStyle: { color: WARN } }],
  }
}

function metricValues(detail: Fhv1ProfileDetail, metric: Fhv1Metric): number[] {
  if (metric === 'variance') return detail.variance
  if (metric === 'std_dev') return detail.std_dev
  return detail.span
}

function pointIndex(params: unknown): number | undefined {
  const entry = Array.isArray(params) ? params[0] : params
  if (!entry || typeof entry !== 'object' || !('dataIndex' in entry)) return undefined
  const dataIndex = entry.dataIndex
  return typeof dataIndex === 'number' ? dataIndex : undefined
}
