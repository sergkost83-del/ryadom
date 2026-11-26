// Сквозной сценарий M2: два соседа из разных домов одного ЖК регистрируются по коду приглашения
// и переписываются в общем чате комплекса. Каждый — в своём браузерном контексте (свой вход).
import { expect, test, type Browser, type Page } from "@playwright/test";
import { existsSync, readFileSync, readdirSync } from "fs";
import { join } from "path";

const MAIL_DIR = process.env.EMAIL_FILE_PATH ?? "/tmp/ryadom-mail";
const INVITES_FILE = process.env.E2E_INVITES_FILE ?? "/tmp/ryadom-invites.json";

/** Код входа берётся из письма, которое сервер записал в файл (режим разработки). */
async function waitForLoginCode(email: string): Promise<string> {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    if (existsSync(MAIL_DIR)) {
      for (const name of readdirSync(MAIL_DIR).filter((f) => f.endsWith(".log")).sort().reverse()) {
        const text = readFileSync(join(MAIL_DIR, name), "utf8");
        const match = text.includes(email) ? text.match(/код входа в РЯДОМ: (\d{6})/) : null;
        if (match) return match[1];
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`Письмо с кодом для ${email} не найдено`);
}

async function registerByInvite(page: Page, email: string, invite: string, name: string) {
  await page.goto("/welcome");
  await page.getByTestId("welcome-start").click();
  await page.getByTestId("email-input").fill(email);
  await page.getByTestId("email-submit").click();
  await expect(page.getByTestId("code-input")).toBeVisible();
  await page.getByTestId("code-input").fill(await waitForLoginCode(email));
  await expect(page.getByTestId("name-input")).toBeVisible();
  await page.getByTestId("name-input").fill(name);
  await page.getByTestId("reg-avatar-2").click();
  await page.getByTestId("mode-invite").click();
  await page.getByTestId("invite-input").fill(invite);
  await page.getByTestId("adult-check").click();
  await page.getByTestId("policy-check").click();
  await page.getByTestId("data-check").click();
  await page.getByTestId("register-submit").click();
  // Код приглашения подтверждает адрес сразу
  await expect(page.getByTestId("address-confirmed")).toBeVisible();
}

async function openCommonChat(page: Page) {
  await page.goto("/chats");
  await page.getByTestId("room-common").click();
  await expect(page.getByTestId("chat-input")).toBeVisible();
}

async function send(page: Page, text: string) {
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
  await expect(page.getByText(text, { exact: true })).toBeVisible();
}

async function twoNeighbours(browser: Browser) {
  const invites = JSON.parse(readFileSync(INVITES_FILE, "utf8")) as { a1: string; a2: string };
  const stamp = Date.now();
  const anna = await browser.newContext();
  const boris = await browser.newContext();
  return {
    stamp,
    invites,
    closeAll: async () => {
      await anna.close();
      await boris.close();
    },
    annaPage: await anna.newPage(),
    borisPage: await boris.newPage(),
  };
}

test("два соседа из разных домов переписываются в общем чате", async ({ browser }) => {
  const { stamp, invites, annaPage, borisPage, closeAll } = await twoNeighbours(browser);
  try {
    await registerByInvite(annaPage, `anna${stamp}@example.com`, invites.a1, "Анна Иванова");
    await registerByInvite(borisPage, `boris${stamp}@example.com`, invites.a2, "Борис Петров");

    const hello = `Привет, соседи! ${stamp}`;
    await openCommonChat(annaPage);
    await send(annaPage, hello);

    await openCommonChat(borisPage);
    await expect(borisPage.getByText(hello, { exact: true })).toBeVisible();
    const reply = `Привет, Анна! ${stamp}`;
    await send(borisPage, reply);

    await annaPage.reload();
    await expect(annaPage.getByText(reply, { exact: true })).toBeVisible();
    // Своё сообщение у автора помечено как своё, чужое — с именем соседа
    await expect(annaPage.getByTestId("chat-message").filter({ hasText: hello })).toBeVisible();
    await expect(annaPage.getByTestId("chat-message").filter({ hasText: reply }).getByText("Борис Петров")).toBeVisible();
  } finally {
    await closeAll();
  }
});

test("сообщение можно удалить и оно исчезает у соседа", async ({ browser }) => {
  const { stamp, invites, annaPage, borisPage, closeAll } = await twoNeighbours(browser);
  try {
    await registerByInvite(annaPage, `anna2${stamp}@example.com`, invites.a1, "Анна Иванова");
    await registerByInvite(borisPage, `boris2${stamp}@example.com`, invites.a2, "Борис Петров");
    const text = `Опечатка ${stamp}`;
    await openCommonChat(annaPage);
    await send(annaPage, text);
    await annaPage.getByTestId("chat-message").filter({ hasText: text }).getByTestId("chat-delete").click();
    await expect(annaPage.getByText(text, { exact: true })).toHaveCount(0);

    await openCommonChat(borisPage);
    await expect(borisPage.getByText(text, { exact: true })).toHaveCount(0);
  } finally {
    await closeAll();
  }
});
