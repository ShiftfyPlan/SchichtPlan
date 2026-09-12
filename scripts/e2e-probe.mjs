/**
 * Authenticated browser probe. Run it before claiming any UI bug is fixed.
 *
 * Built 2026-09-05 after three wrong diagnoses in a row on a blank-screen bug
 * that was only reproducible in a real browser. Static reading of the code
 * could not have found it: the server returned a correct 200, there were no
 * console errors, and the DOM contained 208 KB of script tags with no rendered
 * content. What identified it was measuring `document.body.innerText.length`
 * after a client-side navigation (393) versus after a reload (4636).
 *
 * Usage (from the repo root, Playwright is already a devDependency):
 *
 *   node scripts/e2e-probe.mjs --email x@y.de --password 'pw'
 *   node scripts/e2e-probe.mjs --email … --password … --paths /dashboard,/schichtplan
 *   node scripts/e2e-probe.mjs --email … --password … --shots ./shots
 *   node scripts/e2e-probe.mjs --email … --password … --base http://localhost:3000
 *
 * Reports per page: final URL, visible text length, page errors, console
 * errors, failed requests and CSP violations. A visible text length in the
 * low hundreds means the page rendered nothing but the root layout.
 *
 * Create a throwaway account first (see CLAUDE(schichtplan).md → Tooling), and
 * DELETE IT afterwards. Never probe a real customer's account.
 */
import { chromium } from "@playwright/test";

const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

const BASE = (arg("base", "https://www.shiftfy.de")).replace(/\/$/, "");
const EMAIL = arg("email");
const PASSWORD = arg("password");
const PATHS = (arg("paths", "") || "").split(",").map((s) => s.trim()).filter(Boolean);
const SHOTS = arg("shots");
const WIDTH = Number(arg("width", "1440"));
const HEIGHT = Number(arg("height", "900"));

if (!EMAIL || !PASSWORD) {
  console.error("need --email and --password");
  process.exit(1);
}

// www matters: the apex 307s and a redirect can drop the session cookie.
if (/^https:\/\/shiftfy\.de/.test(BASE)) {
  console.warn("warning: use https://www.shiftfy.de, the apex redirect can drop the session\n");
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: WIDTH, height: HEIGHT } });
const page = await ctx.newPage();

const errs = { pageerror: [], console: [], failed: [], csp: 0 };
page.on("pageerror", (e) => errs.pageerror.push(`${e.name}: ${e.message.slice(0, 220)}`));
page.on("console", (m) => {
  if (m.type() !== "error") return;
  const t = m.text();
  if (/Content Security Policy/i.test(t)) errs.csp++;
  else errs.console.push(t.slice(0, 220));
});
page.on("requestfailed", (r) =>
  errs.failed.push(`${r.failure()?.errorText} ${r.url().replace(BASE, "").slice(0, 110)}`));
page.on("response", (r) => {
  if (r.status() >= 400) errs.failed.push(`HTTP ${r.status()} ${r.url().replace(BASE, "").slice(0, 110)}`);
});

const textLen = async () =>
  (await page.evaluate(() => document.body.innerText.trim())).length;

async function login() {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500); // let hydration settle before typing
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page
    .waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 })
    .catch(() => console.log("!! never left /login — wrong credentials or lockout"));
  await page.waitForTimeout(7000);
}

await login();
console.log(`landed            : ${page.url().replace(BASE, "")}`);
console.log(`visible text (nav): ${await textLen()}`);

// A reload renders server-side; a large gap versus the number above means the
// client-side navigation is broken, not the page.
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(4000);
console.log(`visible text (rld): ${await textLen()}`);

if (SHOTS) {
  const fs = await import("node:fs");
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: `${SHOTS}/landing.png` });
}

for (const p of PATHS) {
  await page.goto(BASE + p, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(3000);
  const redirected = page.url().replace(BASE, "") !== p;
  console.log(
    `${p.padEnd(28)} text=${String(await textLen()).padEnd(6)}` +
      (redirected ? `-> ${page.url().replace(BASE, "")}` : "")
  );
  if (SHOTS) {
    const fs = await import("node:fs");
    await page.screenshot({ path: `${SHOTS}/${p.replace(/\W+/g, "_")}.png` });
  }
}

const show = (label, list) => {
  if (!list.length) return;
  console.log(`\n${label}:`);
  [...new Set(list)].slice(0, 12).forEach((e) => console.log("  ", e));
};
show("page errors", errs.pageerror);
show("console errors", errs.console);
show("failed requests", errs.failed);
if (errs.csp) console.log(`\nCSP violations: ${errs.csp}`);

await browser.close();
