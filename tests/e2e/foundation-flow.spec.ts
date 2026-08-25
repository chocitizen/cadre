import { expect, test } from "@playwright/test";

const ownerEmail = "owner@cadre.test";
const ownerPassword = "CADRE local end-to-end passphrase!";

async function signIn(page: import("@playwright/test").Page) {
  await page.getByLabel("Email").fill(ownerEmail);
  await page.getByLabel("Password").fill(ownerPassword);
  await page.getByRole("button", { name: "Enter CADRE" }).click();
  await expect(page.getByRole("heading", { name: /Good to have you back/ })).toBeVisible();
}

test("owner can persist and reopen a VESSEL conversation and Markdown artifact", async ({
  context,
  page
}) => {
  const conversationTitle = `Foundation verification ${test.info().project.name}`;

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await signIn(page);

  await page.getByRole("link", { name: "Open VESSEL workspace" }).click();
  await expect(page.getByRole("heading", { name: "VESSEL" })).toBeVisible();

  await page.getByLabel("Begin a governed conversation").fill(conversationTitle);
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page.getByRole("heading", { name: conversationTitle })).toBeVisible();

  await page.getByLabel("Message CADRE").fill("Return a concise governed foundation response.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("CADRE test response.", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByText("CADRE test response.", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Save as Markdown" }).click();
  const artifactLink = page.getByRole("link", { name: "Open saved artifact" });
  await expect(artifactLink).toBeVisible();
  await artifactLink.click();
  await expect(
    page.getByRole("heading", { name: `${conversationTitle} — CADRE response` })
  ).toBeVisible();
  await expect(page.getByText("Integrity verified")).toBeVisible();
  await expect(page.getByText("CADRE test response.", { exact: true })).toBeVisible();

  await context.clearCookies();
  await page.goto("/app/ready");
  await expect(page).toHaveURL(/\/login$/);
  await signIn(page);

  await page.goto("/app/ready");
  await page.getByRole("link", { name: new RegExp(conversationTitle) }).click();
  await expect(
    page.getByRole("heading", { name: `${conversationTitle} — CADRE response` })
  ).toBeVisible();
  await expect(page.getByText("Integrity verified")).toBeVisible();
});
