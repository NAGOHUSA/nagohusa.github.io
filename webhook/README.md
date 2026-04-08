# Stripe Webhook Handler — Deployment Guide

The `stripe-handler.js` file is a **Cloudflare Worker** that acts as the bridge
between Stripe and GitHub Actions. It is the only "server-side" component in this
otherwise static stack.

```
Stripe Checkout  →  Cloudflare Worker  →  GitHub repository_dispatch  →  GitHub Actions
  (payment)           (this file)             (API call)                  (invite buyer)
```

---

## Prerequisites

- A [Cloudflare account](https://dash.cloudflare.com) (free tier is fine)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) installed: `npm i -g wrangler`
- A Stripe account with at least one Payment Link configured (see §3)
- A GitHub Personal Access Token (PAT) — see §4

---

## 1. Deploy to Cloudflare Workers

```bash
# From the repo root
cd webhook
wrangler login
wrangler deploy stripe-handler.js --name nagoh-us-stripe-handler --compatibility-date 2024-01-01
```

Note the Worker URL shown after deployment, e.g.:
```
https://nagoh-us-stripe-handler.<your-subdomain>.workers.dev
```

---

## 2. Set Worker environment variables

In the Cloudflare dashboard → Workers → `nagoh-us-stripe-handler` → Settings → Variables,
add the following **secret** environment variables (use "Encrypt" for all):

| Variable | Value |
|---|---|
| `STRIPE_WEBHOOK_SECRET` | From Stripe Dashboard → Webhooks → *Signing secret* (starts with `whsec_`) |
| `GITHUB_TOKEN` | GitHub PAT with `repo` scope (see §4) |
| `GITHUB_REPO_OWNER` | Your GitHub username / org (e.g. `NAGOHUSA`) |
| `GITHUB_REPO_NAME` | The repo hosting this workflow (e.g. `nagohusa.github.io`) |

Or set them via Wrangler:

```bash
wrangler secret put STRIPE_WEBHOOK_SECRET
wrangler secret put GITHUB_TOKEN
wrangler secret put GITHUB_REPO_OWNER
wrangler secret put GITHUB_REPO_NAME
```

---

## 3. Configure Stripe Payment Links

For **each app** you sell:

1. Go to **Stripe Dashboard → Payment Links → Create payment link**.
2. Add your product/price.
3. Under **"After payment"**, leave redirect as default or set a thank-you page URL.
4. Under **"Custom fields"**, add:
   - **Label**: `GitHub Username`
   - **Key**: `github_username`  ← must be exactly this
   - **Type**: Text
   - **Required**: ✅
5. Under **"Metadata"**, add:
   - **Key**: `repo_name`
   - **Value**: the short name of the private repo (e.g. `swift-commerce-kit-ios`) ← must match the repo name in your GitHub account
6. Copy the Payment Link URL into `store/listings.js` → `stripePaymentLink`.

---

## 4. Create a GitHub Personal Access Token (PAT)

The same PAT is used for two things:

| Use | Where |
|---|---|
| Cloudflare Worker calls `repository_dispatch` | `GITHUB_TOKEN` Worker secret |
| GitHub Actions invites the collaborator | `REPO_ACCESS_PAT` Actions secret |

You can use **one** token for both if it has the right scopes.

### Create the token

1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Give it a descriptive note: `nagoh.us marketplace automation`.
4. Select scope: **`repo`** (full repo access — needed to manage collaborators on private repos).
5. Click **Generate token** and copy it immediately.

### Add to GitHub Actions secrets

1. Go to your `nagohusa.github.io` repository → Settings → Secrets and variables → Actions.
2. Click **New repository secret**.
3. Name: `REPO_ACCESS_PAT`, Value: the PAT you just created.

---

## 5. Register the Stripe webhook endpoint

1. Stripe Dashboard → Developers → **Webhooks → Add endpoint**.
2. **Endpoint URL**: `https://nagoh-us-stripe-handler.<your-subdomain>.workers.dev`
3. **Events to listen to**: `checkout.session.completed`
4. Click **Add endpoint**.
5. Copy the **Signing secret** (starts with `whsec_`) and set it as the
   `STRIPE_WEBHOOK_SECRET` Worker secret (step 2).

---

## 6. Test end-to-end

Stripe provides a **test mode** with test card numbers:

```
Card number : 4242 4242 4242 4242
Expiry      : any future date
CVC         : any 3 digits
```

1. Use a test Payment Link in `store/listings.js`.
2. Complete checkout, entering your own GitHub username in the custom field.
3. In Stripe Dashboard → Webhooks → your endpoint → Recent deliveries — you should
   see a `200 OK` response.
4. In GitHub → `nagohusa.github.io` → Actions — you should see the
   **"Grant Repository Access"** workflow run and complete successfully.
5. Check the private repository → Settings → Collaborators — the buyer should appear.

---

## 7. Folder structure overview

```
nagohusa.github.io/
├── index.html                        ← Main storefront (GitHub Pages)
├── store/
│   └── listings.js                   ← Add new apps here
├── webhook/
│   ├── stripe-handler.js             ← Deploy to Cloudflare Workers
│   └── README.md                     ← This file
└── .github/
    └── workflows/
        ├── ads.yml
        └── grant-repo-access.yml     ← Triggered by repository_dispatch
```

---

## Security notes

- The Cloudflare Worker verifies the **Stripe webhook signature** (HMAC-SHA256)
  on every request and rejects events older than 5 minutes (replay attack protection).
- GitHub username and repo name values are **validated against strict regexes**
  in both the Worker and the Actions workflow before any API calls are made.
- The GitHub PAT is stored as an **encrypted secret** in both Cloudflare and GitHub —
  it is never exposed in logs or source code.
- The buyer gets **read-only (`pull`) access** to the repo — they cannot push or
  modify the source history.
