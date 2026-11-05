/**
 * Records the demo video of the real running application (RECORD=1 only).
 * Scene start times are written to submission/video/scenes.json so that
 * scripts/build_demo_video.py can align the narration.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const OUT = path.resolve(__dirname, "../../submission/video");
const narration: { id: string; text: string }[] = JSON.parse(fs.readFileSync(path.join(OUT, "narration.json"), "utf8"));
const durations: Record<string, number> = JSON.parse(fs.readFileSync(path.join(OUT, "durations.json"), "utf8"));

test.skip(process.env.RECORD !== "1", "set RECORD=1 to record the demo video");
test.use({ video: { mode: "on", size: { width: 1440, height: 900 } }, viewport: { width: 1440, height: 900 } });
test.setTimeout(600_000);

test("record demo", async ({ page }) => {
  const t0 = Date.now();
  const scenes: { id: string; start: number }[] = [];
  let sceneStart = 0;
  let current = "";
  const begin = (id: string) => {
    current = id;
    sceneStart = Date.now();
    scenes.push({ id, start: (sceneStart - t0) / 1000 });
  };
  const finish = async () => {
    const need = (durations[current] ?? 0) * 1000 + 900 - (Date.now() - sceneStart);
    if (need > 0) await page.waitForTimeout(need);
  };
  const glide = async (dy: number, steps = 12) => {
    for (let i = 0; i < steps; i++) {
      await page.mouse.wheel(0, dy / steps);
      await page.waitForTimeout(45);
    }
  };
  const corpusRun = process.env.CORPUS_RUN_URL!;

  // S1 — hook
  await page.goto("/");
  await expect(page.getByText("From Mainframe to Modern.")).toBeVisible();
  begin("s1");
  await page.waitForTimeout(2500);
  await glide(500, 20);
  await page.waitForTimeout(1500);
  await glide(-500, 20);
  await finish();

  // S2 — import + overview
  await page.goto("/import");
  begin("s2");
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: "Import sample project" }).click();
  await page.waitForURL(/\/projects\/[0-9a-f]+$/);
  const projectUrl = page.url();
  await expect(page.getByText("RATEENG").first()).toBeVisible();
  await page.waitForTimeout(2500);
  await glide(420);
  await page.waitForTimeout(1500);
  await page.locator("a", { hasText: "OPEN" }).first().hover();
  await finish();

  // S3 — graph + rule
  begin("s3");
  await page.goto(`${projectUrl}/graph`);
  await page.waitForSelector(".react-flow__node");
  await page.waitForTimeout(800);
  await page.locator(".react-flow__node", { hasText: "RATEENG" }).click();
  await page.waitForTimeout(1800);
  await page.goto(`${projectUrl}/rules`);
  await page.getByText("PM-404 Base Premium").click();
  await page.waitForTimeout(1500);
  await glide(520);
  await finish();

  // S4 — generate + traceability
  begin("s4");
  await page.goto(`${projectUrl}/generate`);
  await page.getByRole("button", { name: "Generate RATEENG" }).click();
  await expect(page.getByText("POST /api/v1/rateeng/execute")).toBeVisible();
  await page.getByText("API contract").scrollIntoViewIfNeeded();
  await page.waitForTimeout(2000);
  await page.getByRole("link", { name: "Code" }).first().click();
  await page.waitForSelector("tr.code-line");
  const traced = page.locator("tr.code-line", { hasText: "rounded=True" }).first();
  await traced.scrollIntoViewIfNeeded();
  await page.evaluate(() => document.querySelectorAll<HTMLElement>("div.overflow-auto").forEach((d) => (d.scrollLeft = 0)));
  await page.waitForTimeout(600);
  await traced.locator("td").first().click();
  await page.evaluate(() => document.querySelectorAll<HTMLElement>("div.overflow-auto").forEach((d) => (d.scrollLeft = 0)));
  await finish();

  // S5 — verification
  begin("s5");
  await page.goto(`${projectUrl}/generate`);
  await page.getByRole("link", { name: "Verify" }).last().click();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Run verification" }).click();
  await expect(page.getByText(/^127 of 127 cases produced identical outputs/)).toBeVisible({ timeout: 180_000 });
  await page.waitForTimeout(2500);
  await glide(560);
  await page.waitForTimeout(2500);
  await glide(420);
  await finish();

  // S6 — fault injection
  begin("s6");
  await page.goto(`${projectUrl}/generate`);
  await page.getByText("— drop ROUNDED on RR-BASE-PREMIUM").scrollIntoViewIfNeeded();
  await page.getByText("— drop ROUNDED on RR-BASE-PREMIUM").click();
  await page.waitForTimeout(600);
  await page.getByRole("button", { name: "Generate faulty build & verify" }).click();
  await page.waitForURL(/verify\?gen=/);
  await page.getByRole("button", { name: "Run verification" }).click();
  await expect(page.getByText(/cases differ/)).toBeVisible({ timeout: 180_000 });
  await page.waitForTimeout(1500);
  const cell = page.locator("td", { hasText: "RR-BASE-PREMIUM" }).first();
  await cell.scrollIntoViewIfNeeded();
  await page.mouse.wheel(0, 250);
  await finish();

  // S7 — external repository
  begin("s7");
  await page.goto(corpusRun);
  await expect(page.getByText(/^180 of 180 cases produced identical outputs/)).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(3500);
  await glide(560);
  await page.waitForTimeout(1500);
  await page.getByText("survivors only").click().catch(() => undefined);
  await finish();

  // S8 — close
  begin("s8");
  await page.goto(`${projectUrl}/export`);
  await page.waitForTimeout(2200);
  await page.goto("/");
  await finish();
  await page.waitForTimeout(1200);

  fs.writeFileSync(path.join(OUT, "scenes.json"), JSON.stringify({ scenes, total: (Date.now() - t0) / 1000, narration: narration.map((n) => n.id) }, null, 2));
  const video = page.video();
  await page.close();
  if (video) await video.saveAs(path.join(OUT, "raw-recording.webm"));
});
