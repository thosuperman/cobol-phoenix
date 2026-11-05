/**
 * End-to-end demo workflow (Acts I-IV) against a running backend + frontend.
 * Requires the GnuCOBOL runner for the verification assertions.
 * Set SCREENSHOTS=1 to write submission screenshots.
 */
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const SHOTS = process.env.SCREENSHOTS === "1";
const dir = path.resolve(__dirname, "../../submission/assets/screenshots");

async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(dir, `${name}.png`) });
}

test("import, analyse, generate, verify and detect an injected fault", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("From Mainframe to Modern.")).toBeVisible();
  await shot(page, "01-landing");

  await page.goto("/import");
  await page.getByRole("button", { name: "Import sample project" }).click();
  await page.waitForURL(/\/projects\/[0-9a-f]+$/);
  const projectUrl = page.url();
  await expect(page.getByText("Phoenix Mutual — Auto Premium Rating").first()).toBeVisible();
  await expect(page.getByText("RATEENG").first()).toBeVisible();
  await shot(page, "03-overview");

  await page.goto(`${projectUrl}/graph`);
  await expect(page.getByText("Dependency graph")).toBeVisible();
  await page.waitForSelector(".react-flow__node");
  await shot(page, "04-graph");

  await page.goto(`${projectUrl}/rules`);
  await page.getByText("PM-404 Base Premium").click();
  await expect(page.getByText(/cobol\/RATEENG\.cbl:197-205/).first()).toBeVisible();
  await shot(page, "05-rules");

  await page.goto(`${projectUrl}/generate`);
  await page.getByRole("button", { name: "Generate RATEENG" }).click();
  await expect(page.getByText("rateeng-service").first()).toBeVisible();
  await expect(page.getByText("POST /api/v1/rateeng/execute")).toBeVisible();
  await shot(page, "06-generate");

  await page.getByRole("link", { name: "Code" }).first().click();
  await page.waitForSelector("tr.code-line");
  const traced = page.locator("tr.code-line", { hasText: "rounded=True" }).first();
  await traced.scrollIntoViewIfNeeded();
  await traced.click();
  await expect(page.getByText(/cobol\/RATEENG\.cbl:\d+/).first()).toBeVisible();
  await shot(page, "07-traceability");

  await page.goto(`${projectUrl}/generate`);
  await page.getByRole("link", { name: "Verify" }).last().click();
  await page.getByRole("button", { name: "Run verification" }).click();
  await expect(page.getByText(/cases produced identical outputs in GnuCOBOL and Python/)).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText(/^(\d+) of \1 cases produced identical outputs/)).toBeVisible();
  await shot(page, "08-verification");

  // Act IV: deliberately injected fault must be detected
  await page.goto(`${projectUrl}/generate`);
  await page.getByText("— drop ROUNDED on RR-BASE-PREMIUM").click();
  await page.getByRole("button", { name: "Generate faulty build & verify" }).click();
  await page.waitForURL(/verify\?gen=/);
  await page.getByRole("button", { name: "Run verification" }).click();
  await expect(page.getByText(/cases differ/)).toBeVisible({ timeout: 180_000 });
  const diffCell = page.locator("td", { hasText: "RR-BASE-PREMIUM" }).first();
  await diffCell.scrollIntoViewIfNeeded();
  await expect(diffCell).toBeVisible();
  await page.mouse.wheel(0, 250);
  await shot(page, "09-fault-detected");

  await page.goto(`${projectUrl}/export`);
  await expect(page.getByText("Modernization report")).toBeVisible();
  await shot(page, "10-export");

  await page.goto("/dashboard");
  await expect(page.getByText("Modernization dashboard")).toBeVisible();
  await shot(page, "02-dashboard");
});
