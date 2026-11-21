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
  const result = page.getByText(/FHV1 (PASS|BREACH) lab-\d+/)
  await expect(result).toBeVisible()
  const traceId = (await result.innerText()).match(/lab-\d+/)?.[0]
  expect(traceId).toBeTruthy()

  await page.getByRole('button', { name: 'Live audit' }).click()
  await page.getByRole('button', { name: `Open trace ${traceId ?? ''}` }).click()
  await expect(page.getByRole('region', { name: 'Benchmark explorer' })).toBeVisible()
  const drill = page.getByRole('region', { name: 'fhv1 drill-down' })
  await expect(drill).toBeVisible()
  await expect(drill.getByText(/0x[0-9a-f]{16}/).first()).toBeVisible()
})
