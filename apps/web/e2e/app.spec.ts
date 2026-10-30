import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = (name: string) => path.join(here, "fixtures", name);

async function exportDst(page: Page, name: string): Promise<string> {
  const button = page.getByRole("button", { name: "导出 DST" });
  await expect(button).toBeEnabled();
  const downloadPromise = page.waitForEvent("download");
  await button.click();
  const download = await downloadPromise;
  const target = path.join(test.info().outputDir, name);
  await download.saveAs(target);
  return createHash("sha256").update(readFileSync(target)).digest("hex");
}

async function openApp(page: Page) {
  await page.goto("/");
  await expect(page.locator(".object-row")).toHaveCount(2);
}

test("loads the sample and generates a plan", async ({ page }) => {
  await openApp(page);
  await expect(page.getByText(/已生成/).first()).toBeVisible();
  await expect(page.getByText(/2,564/).first()).toBeVisible();
});

test("add, undo and redo an object", async ({ page }) => {
  await openApp(page);
  await page.getByRole("button", { name: "加矩形" }).click();
  await expect(page.locator(".object-row")).toHaveCount(3);

  await page.getByRole("button", { name: "撤销" }).click();
  await expect(page.locator(".object-row")).toHaveCount(2);

  await page.getByRole("button", { name: "重做" }).click();
  await expect(page.locator(".object-row")).toHaveCount(3);
});

test("edits stitch type and row spacing", async ({ page }) => {
  await openApp(page);
  await page.locator(".object-row").first().click();
  await page.locator("#stitch").selectOption("running");
  await expect(page.locator(".object-row").first()).toContainText("running");

  await page.getByRole("button", { name: "撤销" }).click();
  await expect(page.locator(".object-row").first()).toContainText("fill");

  await page.locator(".object-row").first().click();
  await page.locator("#spacing").fill("0.5");
  await page.locator("#spacing").press("Enter");
  await expect(page.locator("#spacing")).toHaveValue("0.5");
});

test("saves and reopens a project JSON", async ({ page }) => {
  await openApp(page);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "保存工程" }).click();
  const download = await downloadPromise;
  const projectPath = path.join(test.info().outputDir, "project.json");
  await download.saveAs(projectPath);

  await page.locator('input[accept=".json"]').setInputFiles(projectPath);
  await expect(page.getByText(/已打开工程/)).toBeVisible();
  await expect(page.locator(".object-row")).toHaveCount(2);
});

test("imports a DST fixture", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[accept*=".dst"]').setInputFiles(fixture("sample.dst"));
  await expect(page.getByText(/sample\.dst/)).toBeVisible();
  await expect(page.getByText(/导入的文件不可编辑/)).toBeVisible();
});

test("hides and locks an object", async ({ page }) => {
  await openApp(page);
  await page.locator(".object-row").first().click();
  const row = page.locator(".object-row").first();

  await page.getByLabel("隐藏（不生成针迹）").check();
  await expect(row).toHaveClass(/is-hidden/);
  await page.getByLabel("隐藏（不生成针迹）").uncheck();
  await expect(row).not.toHaveClass(/is-hidden/);

  await page.getByLabel("锁定画布编辑").check();
  await expect(row).toHaveClass(/is-locked/);
});

test("duplicates, renames and merges layers", async ({ page }) => {
  await openApp(page);
  const groups = page.locator(".layer-group");
  await expect(groups).toHaveCount(2);

  await page.getByTitle("复制图层").first().click();
  await expect(groups).toHaveCount(3);
  await expect(page.locator(".object-row")).toHaveCount(3);

  const first = groups.first();
  await first.locator(".layer-name").fill("front");
  await first.locator(".layer-name").press("Enter");
  await expect(first.locator(".layer-name")).toHaveValue("front");

  await groups.nth(1).getByTitle("向下合并图层").click();
  await expect(groups).toHaveCount(2);
  await expect(page.locator(".object-row")).toHaveCount(3);

  await groups.first().getByTitle("锁定图层").click();
  await expect(groups.first()).toHaveClass(/is-locked/);
  await groups.first().getByTitle("解锁图层").click();
  await expect(groups.first()).not.toHaveClass(/is-locked/);
});

test("100 edits and undos restore an identical DST", async ({ page }) => {
  await openApp(page);
  await expect(page.getByText(/已生成/).first()).toBeVisible();
  const before = await exportDst(page, "before.dst");

  await page.locator(".object-row").first().click();
  for (let index = 0; index < 100; index += 1) {
    await page.keyboard.press("ArrowRight");
  }
  for (let index = 0; index < 100; index += 1) {
    await page.keyboard.press("Control+z");
  }
  await expect(page.getByText(/已生成/).first()).toBeVisible();

  const after = await exportDst(page, "after.dst");
  expect(after).toBe(before);
});

test("exports a DST", async ({ page }) => {
  await openApp(page);
  const button = page.getByRole("button", { name: "导出 DST" });
  await expect(button).toBeEnabled();
  const downloadPromise = page.waitForEvent("download");
  await button.click();
  const download = await downloadPromise;
  const exportPath = path.join(test.info().outputDir, "export.dst");
  await download.saveAs(exportPath);
  const size = (await import("node:fs")).statSync(exportPath).size;
  expect(size).toBeGreaterThan(1000);
});
