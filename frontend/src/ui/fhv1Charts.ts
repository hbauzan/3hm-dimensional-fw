import type { EChartsCoreOption } from 'echarts/core'
import {
  FHV1_QUADRANTS,
  formatLosslessF64,
  formatViolationMagnitudeDirection,
  isFhv1RogueDim,
  movementTierName,
  type Fhv1DimView,
  type Fhv1Metric,
  type Fhv1ProfileDetail,
} from '../domain/fhv1.ts'

const AXIS = '#94a3b8'
const ACCENT = '#38bdf8'
const PASS = '#10b981'
const WARN = '#f59e0b'
const FAIL = '#ef4444'
const OBSERVED = '#e2e8f0'

const QUADRANT_COLORS: Record<(typeof FHV1_QUADRANTS)[number], string> = {
  IN_DOMAIN_VALID: PASS,
  OUT_OF_DOMAIN_BENIGN: ACCENT,
  HYBRID_BOUNDARY: WARN,
  ADVERSARIAL_FUZZING: FAIL,
}

export type Fhv1HistogramMode = 'global' | 'per_category'

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
  return {
    textStyle: { color: AXIS },
    tooltip: { trigger: 'axis', formatter: (params: unknown) => envelopeTooltip(detail, params) },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: dims, axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS }, scale: true },
    series: envelopeBandSeries(detail.min, detail.max, detail.mean),
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

/** Builds a numerically sorted failed-dimensions histogram chart for global or 4-quadrant overlay. */
export function failedDimsHistogramOption(
  globalHistogram: Record<string, number> | null,
  byCategory: Record<string, Record<string, number>> | null,
  mode: Fhv1HistogramMode,
): EChartsCoreOption {
  const keys = sortedHistogramKeys(globalHistogram, byCategory, mode)
  const series =
    mode === 'global'
      ? [
          {
            name: 'failed_dims_count',
            type: 'bar',
            data: keys.map((key) => globalHistogram?.[key] ?? 0),
            itemStyle: { color: ACCENT },
          },
        ]
      : FHV1_QUADRANTS.map((quadrant) => ({
          name: quadrant,
          type: 'bar',
          data: keys.map((key) => byCategory?.[quadrant]?.[key] ?? 0),
          itemStyle: { color: QUADRANT_COLORS[quadrant] },
        }))
  return {
    textStyle: { color: AXIS },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const index = pointIndex(params)
        if (index === undefined) return ''
        const bucket = keys[index]
        if (bucket === undefined) return ''
        if (mode === 'global') {
          return `failed_dims ${bucket}\ncount ${formatLosslessF64(globalHistogram?.[bucket] ?? 0)}`
        }
        const lines = [`failed_dims ${bucket}`]
        for (const quadrant of FHV1_QUADRANTS) {
          lines.push(`${quadrant} ${formatLosslessF64(byCategory?.[quadrant]?.[bucket] ?? 0)}`)
        }
        return lines.join('\n')
      },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: keys, axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS } },
    series,
  }
}

/** Formats a lossless IEEE 754 binary64 tooltip for one drill-down dimension. */
export function drilldownTooltip(dimensions: readonly Fhv1DimView[], params: unknown): string {
  const dimIndex = pointIndex(params)
  if (dimIndex === undefined) return ''
  const dim = dimensions[dimIndex]
  if (!dim) return ''
  const normPos = dim.norm_pos === null ? 'null' : formatLosslessF64(dim.norm_pos)
  return [
    `dim ${dimIndex}`,
    `status ${dim.status}`,
    `x ${formatLosslessF64(dim.observed)}`,
    `min ${formatLosslessF64(dim.min)}`,
    `max ${formatLosslessF64(dim.max)}`,
    `mean ${formatLosslessF64(dim.mean)}`,
    `violation_delta ${formatViolationMagnitudeDirection(dim)}`,
    `delta_vs_mean ${formatLosslessF64(dim.delta_vs_mean)}`,
    `norm_pos ${normPos}`,
  ].join('\n')
}

/** Overlays a chunk's observed vector across the [min, max] envelope and mean baseline. */
export function drilldownVectorOption(dimensions: readonly Fhv1DimView[]): EChartsCoreOption {
  const dims = dimensions.map((_, index) => index)
  const mins = dimensions.map((dim) => dim.min)
  const maxs = dimensions.map((dim) => dim.max)
  const means = dimensions.map((dim) => dim.mean)
  const observed = dimensions.map((dim) => (dim.status === 'pruned_rogue' ? null : dim.observed))
  const prunedRogue = dimensions.map((dim) => (dim.status === 'pruned_rogue' ? dim.observed : null))
  const breaches = dimensions.map((dim) =>
    dim.status === 'underflow' || dim.status === 'overflow' ? dim.observed : null,
  )
  return {
    textStyle: { color: AXIS },
    tooltip: { trigger: 'axis', formatter: (params: unknown) => drilldownTooltip(dimensions, params) },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    xAxis: { type: 'category', data: dims, axisLabel: { color: AXIS } },
    yAxis: { type: 'value', axisLabel: { color: AXIS }, scale: true },
    series: [
      ...envelopeBandSeries(mins, maxs, means),
      {
        name: 'observed',
        type: 'line',
        data: observed,
        connectNulls: false,
        symbol: 'none',
        lineStyle: { color: OBSERVED, width: 1.5 },
      },
      {
        name: 'pruned_rogue',
        type: 'scatter',
        data: prunedRogue,
        itemStyle: { color: WARN },
        symbol: 'diamond',
      },
      {
        name: 'breach',
        type: 'scatter',
        data: breaches,
        itemStyle: { color: FAIL },
        symbol: 'circle',
        symbolSize: 7,
      },
    ],
  }
}

function envelopeBandSeries(
  mins: readonly number[],
  maxs: readonly number[],
  means: readonly number[],
) {
  const band = maxs.map((value, index) => value - (mins[index] ?? 0))
  return [
    {
      name: 'min',
      type: 'line',
      data: mins,
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
    { name: 'mean', type: 'line', data: means, symbol: 'none', lineStyle: { color: PASS } },
  ]
}

function sortedHistogramKeys(
  globalHistogram: Record<string, number> | null,
  byCategory: Record<string, Record<string, number>> | null,
  mode: Fhv1HistogramMode,
): string[] {
  const distinct = new Set<string>()
  if (mode === 'global') {
    for (const key of Object.keys(globalHistogram ?? {})) distinct.add(key)
  } else {
    for (const quadrant of FHV1_QUADRANTS) {
      for (const key of Object.keys(byCategory?.[quadrant] ?? {})) distinct.add(key)
    }
  }
  return Array.from(distinct).sort((left, right) => Number(left) - Number(right))
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
