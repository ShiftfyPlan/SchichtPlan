# CLAUDE(schichtplan).md

Session handover. Last updated 2026-09-12.

> Naming note: Claude Code auto-loads `CLAUDE.md`, not this filename. This file
> was named on explicit instruction; it must be opened manually or symlinked.

## What this is

- German B2B shift-planning SaaS, brand **Shiftfy**, live at `https://www.shiftfy.de`.
- Repo `eltahawyomar001-eng/SchichtPlan`, deploys on push to `main` (Vercel, project `schichtplan`, team `omar-fahmys-projects-87bdb2b3`).
- Next.js 16 (App Router) + Prisma 7 + Supabase Postgres (eu-west-1) + NextAuth + Stripe + Resend.
- Repositioning from generic scheduling to **"Zoll-Shield"**: a compliance product for the German private-security sector (§34a GewO, ArbZG, MiLoG, FKS/Zoll audits).
- Companion Expo app at `/Users/omarrageh/shiftfy-mobile` (separate repo `eltahawyomar001-eng/shiftfy-mobile`), talks to this app as a BFF.

## Always use `www.shiftfy.de`

- The apex `shiftfy.de` 307s to `www`; the redirect can drop the session cookie and produce confusing auth errors. Every probe, link and test must use `www`.

## People and accounts

- **Omar Rageh** — owner/operator. Shiftfy login `omarragehfulda@gmail.com`; real workspace id `cmqodw2v0000104jv2mxwbutz`.
- **Mo (Mohamed Bashabsheh)** — business partner. Not a Shiftfy user; told on 2026-08-31 to register.
- **Lara Luise Jennings** — admin at Axiom24, contacts Omar directly on WhatsApp.
- **Axiom24 Facility Management** (`cmnz5cjq8000004joc9uh41kc`) — 12 users, heaviest real user. **Agreed free pilot**; subscription row hand-set to ACTIVE/PROFESSIONAL until 2027-05-24 with no Stripe customer. Not billed.
- **SD MONT** (`elzahrykhaled@gmail.com`) — Omar's own test signup, 2026-09-05. BASIC/TRIALING, trial ends **2026-09-19**, no card yet.
- **Europa Passage Hamburg** — real trial, ends **2026-09-17**. First account that will receive the new trial-reminder emails.

## Where credentials live (never the values)

- Production env: `npx vercel env ls production --token <token>`; pull with `vercel env pull <file>` and delete the file afterwards.
- `.env.local` in this repo already holds the production `DATABASE_URL`/`DIRECT_URL`.
- `prisma.config.ts` resolves `DIRECT_URL` from `.env.local`, so **`prisma migrate dev` targets PRODUCTION** and can prompt a destructive reset. Never run it unguarded.
- Raw Postgres TCP (5432/6543) is blocked from the dev sandbox. Use the Supabase MCP (`execute_sql`, `apply_migration`) for all DB work.
- The Supabase MCP points at _this_ project. For VergabeFlow it points at the wrong project.
- Omar pastes live secrets into chat. Use them, never echo them back, always tell him to rotate.

## Conventions he has insisted on

- **Verify before claiming.** Never say something is fixed without observing it working. On 2026-09-05 three consecutive "it's fixed" claims were wrong; he replied "stop hallucinating". Use `scripts/e2e-probe.mjs`.
- **No em dashes or double hyphens** in prose written for him. Much of it goes straight to clients.
- **Always add an English translation** under any German text written for him, unasked.
- **Never emojis as icons.** Custom SVG only.
- **Commit and push after every fix or feature.**
- **Never create or push remote branches without explicit approval.** Deploys target `main`/production only; there is no staging branch.
- **No hardcoded UI strings.** Everything through next-intl (`messages/de.json`, `messages/en.json`), including SEO pages.
- **Never hardcode dark-only or light-only.** Every colour needs both.
- **Render and view visual output at real size before shipping it.**
- **Do not spawn subagents, workflows or deep research unless asked.**
- **When asked to plan or audit, do not implement.**
- Mobile: decouple native data extraction from presentation; never ship default system UI.
- The mobile repo's `AGENTS.md` requires reading the versioned Expo SDK docs before writing code there. It matters: `mocked` is top-level on `LocationObject`, and `getCurrentPositionAsync` has no timeout option.

## Decisions and reasoning

- **Stripe is LIVE**, account `acct_1TOkuKLWrEpbJgVN`, KYC complete, charges and payouts enabled. Earlier notes calling it sandbox are wrong.
- **Revenue is €0.** Not a broken funnel: four real companies reached Stripe Checkout Jul–Aug 2026 and all five sessions expired unpaid.
- `tax_id_collection` removed from checkout — it asked German Kleinunternehmer (§19 UStG) for a USt-IdNr to pay €0.00 that day.
- `billing_address_collection` deliberately stays **required**: §14 UStG obliges a recipient address on German invoices, and the webhook builds `Invoice.recipientAddress` from it.
- `REQUIRE_CARD_AT_SIGNUP=true` is **on in production**. Gates OWNER/ADMIN only; gating others would strand employees who cannot reach checkout. Punch clock (`/stempel`) sits outside the dashboard route group so ArbZG §16 clocking survives.
- `securitySectorMode` defaults **false** so the §34a inversion cannot silently break existing customers. Inferring it from the free-text `industry` field was rejected — it is NULL everywhere.
- Compliance overrides are a first-class table, not `AuditLog` entries: an auditor needs to know _why_ a block was released, and `entityId` is deliberately not a foreign key so an override outlives its shift.
- Unattended paths (auto-fill, SOS) get **no** override path — there is no dispatcher present to justify one.
- Geofence distance is always computed **server-side**; a client-reported distance or verdict is never trusted.
- The FKS PDF is deliberately **not** behind the PDF quota or plan gate: an FKS audit is unannounced and a billing counter must not become a legal problem.
- CSP nonce + `strict-dynamic` was **removed**. A per-request nonce breaks every client-side navigation, because the browser enforces the document's CSP. `unsafe-inline` only applies when no nonce is present. Restoring nonce protection means making the nonce stable per document.
- Login uses a **full page load** after `signIn`, not `router.push`: the App Router's pre-auth RSC cache otherwise renders the destination from a signed-out tree.
- Vercel **Skew Protection** enabled (12 h) plus `deploymentId`. Useful, but it did _not_ fix the blank screen; that was the CSP and login issues.

## Tooling built here

- `scripts/ui-audit.py` — static design-token drift audit, read-only. `python3 scripts/ui-audit.py [--json out.json]`. 2026-09-05 baseline is in its docstring; every number should fall after token work.
- `scripts/e2e-probe.mjs` — authenticated browser probe. `node scripts/e2e-probe.mjs --email … --password … [--paths /a,/b] [--shots ./dir]`. Compares visible text after client navigation versus reload; a few hundred characters means nothing rendered.
- Throwaway test accounts: insert Workspace + User (bcrypt hash via `node -e "console.log(require('bcryptjs').hashSync('pw',10))"`) + Subscription through the Supabase MCP, then **delete all three rows afterwards**. Give the subscription a fake `stripeSubscriptionId` to bypass the card gate. Never probe a real customer account.
- `npx vercel redeploy <url> --scope omar-fahmys-projects-87bdb2b3 --token …` — env vars only bind at build time, so adding one needs a redeploy.

## Finished

- Zoll-Shield phases 1–4.5: schema foundation, universal compliance gate (`src/lib/compliance-gate.ts`), server-authoritative geofencing, dispatcher override UI, FKS PDF export, Bewacherregister fields, demo seeder.
- All four shift-write paths route through `assertShiftCompliance`: `/api/shifts`, `/api/shifts/[id]`, timesheet-import approve, auto-fill, plus SOS ranking and acceptance.
- Location geocoding now persists to the DB; geofence settings UI on `/standorte`.
- `ComplianceOverride` records surfaced on `/pruefungssicher` and in the FKS PDF.
- Upstash Redis configured in production (login lockout, caches, JWT claims were all running on per-lambda memory before).
- Trial reminder emails at 7/3/1 days: `/api/cron/trial-reminders`, daily 06:00.
- Test suite green: **1269 passing**. `Quote` and `CustomerInvoice` added to `SCOPED_MODELS`; two time-entry tests fixed (they hardcoded a date that drifted out of the 30-day backdating window — keep test dates relative).
- Axiom24 data exported to `/Users/omarrageh/shiftfy-exports/axiom24-shiftfy-export-2026-09-05.zip` (customer PII, deliberately outside the repo, never commit it).
- Phase 0 UI audit published: https://claude.ai/code/artifact/9fd9c21b-e545-484e-be43-568c5b5e5922

## Open

- **Rotate the Vercel and Upstash tokens** pasted in chat 2026-09-05. The Vercel one reads the live Stripe key and DB URL.
- **No real subscription has ever completed.** The webhook path from `checkout.session.completed` to ACTIVE is unproven in production.
- **`step4Title` / `step4Desc` render as literal strings** in the onboarding checklist, on the first screen a new signup sees.
- Cookie banner and product tour open as competing modals on first load.
- `rounded-square` is not a Tailwind class and silently does nothing.
- Dark mode is 0% on `/stempel` and `/station` — the two screens guards hold.
- Mobile-viewport audit never completed; the capture run failed.
- `securitySectorMode` is false on all 12 workspaces, so the §34a inversion is dormant.
- `GEOFENCE` exists in `ComplianceRule` and is accepted as a bypass flag, but the gate never evaluates it — only the clock route does.
- Axiom24 still unbilled; converting them means a card, since they have no Stripe customer.
- `/api/admin/seed-fks-demo` is a mutating **GET** in production. It reassigns the caller's workspace and should be deleted after demos.
- Prices are €2.99/user/mo Basic and €4.99 Professional. Worth revisiting whether that signals the value of a compliance product.
- UI redesign: audit says token problem first, redesign second. Fix the live defects, collapse four neutral ramps to one with an ESLint rule, then decide direction — that last step needs a designer or Omar's taste.
