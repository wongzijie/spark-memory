import { expect, test } from "@playwright/test";

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for the end-to-end test`);
  return value;
}

test("admin sees a Telegram text capture", async ({ page, request }) => {
  const sparkText = `来自 Telegram 的第一条 Spark · ${Date.now()}`;
  const senderId = Number(process.env.E2E_TELEGRAM_USER_ID ?? "7788");
  const updateId = Date.now();

  const webhook = await request.post(
    `${required("E2E_API_URL")}/api/telegram/webhook/${required("E2E_WEBHOOK_PATH")}`,
    {
      headers: {
        "X-Telegram-Bot-Api-Secret-Token": required("E2E_WEBHOOK_HEADER"),
      },
      data: {
        update_id: updateId,
        message: {
          message_id: updateId,
          date: Math.floor(Date.now() / 1000),
          chat: { id: senderId, type: "private" },
          from: { id: senderId, is_bot: false, first_name: "Owner" },
          text: sparkText,
        },
      },
    },
  );
  expect(webhook.ok(), await webhook.text()).toBeTruthy();

  await page.goto("/login");
  await page.getByLabel("邮箱").fill(required("E2E_ADMIN_EMAIL"));
  await page.getByLabel("密码").fill(required("E2E_ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /进入记忆本/ }).click();

  await expect(page).toHaveURL("/");
  await expect
    .poll(
      async () => {
        await page.reload();
        return page.getByText(sparkText, { exact: true }).isVisible();
      },
      { timeout: 20_000 },
    )
    .toBe(true);
  await expect(page.getByText("已处理").first()).toBeVisible();
});
