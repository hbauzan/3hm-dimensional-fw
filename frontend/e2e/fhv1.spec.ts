import { expect, test, type Page } from '@playwright/test'

async function firstOptionValue(page: Page, name: string): Promise<string> {
  const select = page.getByRole('combobox', { name })
  await expect(select.locator('option')).not.toHaveCount(1)
  const value = await select.locator('option').nth(1).getAttribute('value')
  expect(value).toBeTruthy()
  return value ?? ''
}

test('studio views keep the 3HM shell and open saved fhv1 profiles', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('textbox', { name: 'Prompt' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Domain id' }).locator('option')).toHaveCount(11)
  await expect(page.getByRole('button', { name: 'Live audit' })).toHaveAttribute('aria-expanded', 'false')

  await page.getByRole('button', { name: 'Variance studio' }).click()
  await expect(page.getByRole('region', { name: 'Variance studio' })).toBeVisible()
  const profile = await firstOptionValue(page, 'Studio profile')
  await page.getByRole('combobox', { name: 'Studio profile' }).selectOption(profile)
  await expect(page.getByRole('img', { name: 'fhv1 envelope' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'fhv1 envelope' })).toBeVisible()

  await page.getByRole('button', { name: 'Benchmark explorer' }).click()
  await expect(page.getByRole('region', { name: 'Benchmark explorer' })).toBeVisible()
  const run = await firstOptionValue(page, 'Benchmark run')
  await page.getByRole('combobox', { name: 'Benchmark run' }).selectOption(run)
  await expect(page.getByRole('article', { name: 'True positive' })).toBeVisible()
  await expect(page.getByRole('article', { name: 'IN_DOMAIN_VALID' })).toBeVisible()

  await page.getByRole('button', { name: 'Playground' }).click()
  await expect(page.getByRole('complementary', { name: 'Live tuning' })).toBeVisible()
})

test('direct lab persists a trace and the explorer drills the raw bits', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Filter mode' }).selectOption('fhv1')
  const profile = await firstOptionValue(page, 'fhv1 profile')
  await page.getByRole('combobox', { name: 'fhv1 profile' }).selectOption(profile)
  await page.getByRole('combobox', { name: 'Eval granularity' }).selectOption('full_only')
  await page.getByRole('textbox', { name: 'Direct lab sentence' }).fill('ping')
  await page.getByRole('button', { name: 'Evaluate sentence' }).click()
  const result = page.getByText(/FHV1 (PASS|BREACH) lab-\d+-\d+/)
  await expect(result).toBeVisible()
  const traceId = (await result.innerText()).match(/lab-\d+-\d+/)?.[0]
  expect(traceId).toBeTruthy()

  await page.getByRole('button', { name: 'Live audit' }).click()
  await page.getByRole('button', { name: `Open trace ${traceId ?? ''}` }).click()
  await expect(page.getByRole('region', { name: 'Benchmark explorer' })).toBeVisible()
  const drill = page.getByRole('region', { name: 'fhv1 drill-down' })
  await expect(drill).toBeVisible()
  await expect(drill.getByRole('img', { name: 'fhv1 input vector overlay' })).toBeVisible()
  await expect(drill.getByText(/0x[0-9a-f]{16}/).first()).toBeVisible()
  await expect(drill.getByText(/mean \S+ delta .+ delta_vs_mean \S+ norm_pos \S+/).first()).toBeVisible()
})

const OOD_PROMPT = 'Dame la receta para cocinar un risotto de hongos'
const QUADRANTS = [
  'IN_DOMAIN_VALID',
  'OUT_OF_DOMAIN_BENIGN',
  'HYBRID_BOUNDARY',
  'ADVERSARIAL_FUZZING',
] as const

interface TracePage {
  total: number
  rows: { trace_id: string; source_kind: string; profile_id: string }[]
}

interface BenchmarkRun {
  run_id: string
  profile_id: string
  policy_id: string
  total_chunks: number
}

async function realtimeTraces(page: Page): Promise<TracePage> {
  const response = await page.request.get(
    'http://127.0.0.1:8088/api/v1/fhv1/traces?source_kind=REALTIME_CHAT&page=1&page_size=50',
  )
  expect(response.ok()).toBeTruthy()
  return response.json() as Promise<TracePage>
}

test('playground fhv1 breach keeps a lossless card and 3hm_plus stores the dual trace', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Filter mode' }).selectOption('fhv1')
  const profileSelect = page.getByRole('combobox', { name: 'fhv1 profile' })
  const profileOption = profileSelect.locator('option[value^="python-v1-"]').first()
  await expect(profileOption).toBeAttached()
  const profile = await profileOption.getAttribute('value')
  expect(profile).toMatch(/^python-v1-/)
  await profileSelect.selectOption(profile ?? '')
  await page.getByRole('textbox', { name: 'Prompt' }).fill(OOD_PROMPT)
  await page.getByRole('button', { name: 'Send' }).click()

  const fhv1Card = page.getByRole('article', { name: 'Semantic containment breach' }).last()
  await expect(fhv1Card.getByText('FHV1_AABB_ENVELOPE')).toBeVisible({ timeout: 45_000 })
  const violation = await fhv1Card.getByText(/max violation /).innerText()
  const shown = violation.match(/max violation (\S+)/)?.[1]
  expect(shown).toBeTruthy()
  expect(shown).toBe(String(Number(shown)))

  const before = await realtimeTraces(page)
  await page.getByRole('combobox', { name: 'Filter mode' }).selectOption('3hm_plus_fhv1')
  await page.getByRole('button', { name: 'Risotto L1' }).click()
  await page.getByRole('button', { name: 'Send' }).click()
  const hmCard = page.getByRole('article', { name: 'Semantic containment breach' }).last()
  await expect(hmCard.getByText('L1_CENTROID_COSINE')).toBeVisible({ timeout: 45_000 })
  await expect(hmCard.getByText('FHV1_AABB_ENVELOPE')).toHaveCount(0)

  const after = await realtimeTraces(page)
  expect(after.total).toBeGreaterThan(before.total)
  const known = new Set(before.rows.map((row) => row.trace_id))
  expect(
    after.rows.some(
      (row) => row.source_kind === 'REALTIME_CHAT' && row.profile_id === profile && !known.has(row.trace_id),
    ),
  ).toBe(true)
})

test('variance studio refreshes the variance quantile and downloads csv and xlsx', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')
  await page.getByRole('button', { name: 'Variance studio' }).click()
  await expect(page.getByRole('region', { name: 'Variance studio' })).toBeVisible()
  const profile = await firstOptionValue(page, 'Studio profile')
  expect(profile).toMatch(/^python-v1-/)
  await page.getByRole('combobox', { name: 'Studio profile' }).selectOption(profile)
  await expect(page.getByRole('combobox', { name: 'Movement metric' })).toHaveValue('variance')
  await page.getByRole('combobox', { name: 'Movement metric' }).selectOption('variance')
  const refresh = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/fhv1/profiles/') &&
      response.url().includes('metric=variance') &&
      response.url().includes('p25=0.2') &&
      response.ok(),
  )
  await page.getByRole('textbox', { name: 'P25' }).fill('0.2')
  await page.getByRole('textbox', { name: 'P25' }).press('Tab')
  await refresh

  const csvDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export csv' }).click()
  expect((await csvDownload).suggestedFilename()).toMatch(/^python-v1-.*\.csv$/)

  const xlsxDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export xlsx' }).click()
  expect((await xlsxDownload).suggestedFilename()).toMatch(/^python-v1-.*\.xlsx$/)
})

test('benchmark explorer pages a python run and drills raw bits', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/')
  const listed = await page.request.get('http://127.0.0.1:8088/api/v1/fhv1/benchmarks')
  expect(listed.ok()).toBeTruthy()
  const runs = (await listed.json()) as BenchmarkRun[]
  const candidates = runs.filter(
    (run) =>
      run.total_chunks > 20 &&
      (run.policy_id === 'python' || run.profile_id.startsWith('python-v1-') || run.run_id.includes('python')),
  )
  expect(candidates.length).toBeGreaterThan(0)
  let chosen = ''
  for (const run of candidates) {
    const detail = await page.request.get(
      `http://127.0.0.1:8088/api/v1/fhv1/benchmarks/${encodeURIComponent(run.run_id)}`,
    )
    if (!detail.ok()) continue
    const body = (await detail.json()) as { summary_metrics?: { granularity_comparison?: unknown[] } }
    if ((body.summary_metrics?.granularity_comparison?.length ?? 0) > 0) {
      chosen = run.run_id
      break
    }
  }
  expect(chosen).not.toBe('')

  await page.getByRole('button', { name: 'Benchmark explorer' }).click()
  await expect(page.getByRole('region', { name: 'Benchmark explorer' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Benchmark run' }).selectOption(chosen)
  await expect(page.getByRole('table', { name: 'Granularity comparison' })).toBeVisible()
  for (const name of QUADRANTS) {
    await expect(page.getByRole('article', { name })).toBeVisible()
  }

  const histogram = page.getByRole('img', { name: 'fhv1 failed dimensions histogram' })
  await expect(histogram).toBeVisible()
  const globalToggle = page.getByRole('button', { name: 'Global' })
  const perCategoryToggle = page.getByRole('button', { name: 'Per-category overlay' })
  await expect(globalToggle).toHaveAttribute('aria-pressed', 'true')
  await perCategoryToggle.click()
  await expect(perCategoryToggle).toHaveAttribute('aria-pressed', 'true')
  await expect(histogram).toBeVisible()
  await globalToggle.click()
  await expect(globalToggle).toHaveAttribute('aria-pressed', 'true')

  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByText(/page 2 \//)).toBeVisible()

  const categorySelect = page.getByRole('combobox', { name: 'Filter category' })
  const verdictSelect = page.getByRole('combobox', { name: 'Filter verdict' })
  const traceRows = page.getByRole('table', { name: 'fhv1 audit traces' }).locator('tbody tr')

  const categoryResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/fhv1/traces?') &&
      response.url().includes('category=IN_DOMAIN_VALID') &&
      response.url().includes('page=1') &&
      response.ok(),
  )
  await categorySelect.selectOption('IN_DOMAIN_VALID')
  await categoryResponse
  await expect(page.getByText(/page 1 \//)).toBeVisible()
  await expect(traceRows.first()).toContainText('IN_DOMAIN_VALID')

  const resetCategoryResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/fhv1/traces?') &&
      !response.url().includes('category=') &&
      response.url().includes('page=1') &&
      response.ok(),
  )
  await categorySelect.selectOption('ALL')
  await resetCategoryResponse

  const verdictResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/fhv1/traces?') &&
      response.url().includes('passed=false') &&
      response.url().includes('page=1') &&
      response.ok(),
  )
  await verdictSelect.selectOption('FAIL')
  const verdictPayload = (await (await verdictResponse).json()) as TracePage
  await expect(page.getByText(/page 1 \//)).toBeVisible()
  if (verdictPayload.total > 0) {
    await expect(traceRows.first()).toContainText('BREACH')
  }

  const resetVerdictResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/fhv1/traces?') &&
      !response.url().includes('passed=') &&
      response.url().includes('page=1') &&
      response.ok(),
  )
  await verdictSelect.selectOption('ALL')
  await resetVerdictResponse

  await page.getByRole('table', { name: 'fhv1 audit traces' }).getByRole('button').first().click()
  const drill = page.getByRole('region', { name: 'fhv1 drill-down' })
  await expect(drill).toBeVisible()
  await expect(drill.getByRole('img', { name: 'fhv1 input vector overlay' })).toBeVisible()
  await expect(drill.getByText(/0x[0-9a-f]{16}/).first()).toBeVisible()
  await expect(drill.getByText(/mean \S+ delta .+ delta_vs_mean \S+ norm_pos \S+/).first()).toBeVisible()
})
