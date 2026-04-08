/**
 * stripe-handler.js — Cloudflare Worker
 *
 * Receives Stripe webhook events, verifies the signature, and triggers a
 * GitHub Actions `repository_dispatch` event so the grant-repo-access workflow
 * can invite the buyer as a collaborator to the correct private repo.
 *
 * Deploy to Cloudflare Workers (free tier):
 *   https://developers.cloudflare.com/workers/get-started/guide/
 *
 * Required environment variables (set in the Cloudflare dashboard):
 *   STRIPE_WEBHOOK_SECRET   — from Stripe Dashboard → Webhooks → Signing secret
 *   GITHUB_TOKEN            — GitHub PAT with `repo` scope on nagohusa.github.io
 *   GITHUB_REPO_OWNER       — your GitHub username/org (e.g. "NAGOHUSA")
 *   GITHUB_REPO_NAME        — the repo that holds the workflow (e.g. "nagohusa.github.io")
 */

export default {
  async fetch(request, env) {
    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    const body = await request.text();
    const signature = request.headers.get('stripe-signature');

    if (!signature) {
      return new Response('Missing stripe-signature header', { status: 400 });
    }

    // ── 1. Verify Stripe webhook signature ────────────────────────────────────
    const isValid = await verifyStripeSignature(body, signature, env.STRIPE_WEBHOOK_SECRET);
    if (!isValid) {
      console.error('Stripe signature verification failed');
      return new Response('Unauthorized', { status: 401 });
    }

    // ── 2. Parse the event ────────────────────────────────────────────────────
    let event;
    try {
      event = JSON.parse(body);
    } catch {
      return new Response('Invalid JSON', { status: 400 });
    }

    // We only care about successful checkouts
    if (event.type !== 'checkout.session.completed') {
      return new Response('OK — ignored event type', { status: 200 });
    }

    const session = event.data.object;

    // Payment must be paid (not just initiated)
    if (session.payment_status !== 'paid') {
      return new Response('OK — payment not yet paid', { status: 200 });
    }

    // ── 3. Extract buyer's GitHub username ────────────────────────────────────
    //
    // In the Stripe Payment Link / Checkout settings, add a Custom Field:
    //   Label : "GitHub Username"
    //   Key   : github_username
    //   Type  : text  (required)
    //
    const customFields = session.custom_fields ?? [];
    const githubField = customFields.find(f => f.key === 'github_username');
    const githubUsername = githubField?.text?.value?.trim();

    if (!githubUsername) {
      console.error('github_username not found in custom_fields', JSON.stringify(customFields));
      return new Response('Missing github_username custom field', { status: 422 });
    }

    // ── 4. Determine which private repo to grant access to ───────────────────
    //
    // In the Stripe Payment Link settings, add Metadata:
    //   Key   : repo_name
    //   Value : the short name of the private repo (e.g. "swift-commerce-kit-ios")
    //
    // The metadata flows through to checkout.session.metadata automatically.
    //
    const repoName = session.metadata?.repo_name?.trim();

    if (!repoName) {
      console.error('repo_name not found in session metadata', JSON.stringify(session.metadata));
      return new Response('Missing repo_name metadata on Payment Link', { status: 422 });
    }

    // ── 5. Validate extracted values ──────────────────────────────────────────
    if (!/^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$/.test(githubUsername)) {
      return new Response('Invalid github_username value', { status: 422 });
    }
    if (!/^[a-zA-Z0-9._-]{1,100}$/.test(repoName)) {
      return new Response('Invalid repo_name value', { status: 422 });
    }

    // ── 6. Trigger GitHub Actions via repository_dispatch ─────────────────────
    const dispatchUrl = `https://api.github.com/repos/${env.GITHUB_REPO_OWNER}/${env.GITHUB_REPO_NAME}/dispatches`;

    const payload = {
      event_type: 'stripe-payment-success',
      client_payload: {
        github_username: githubUsername,
        repo_name:       repoName,
        payment_intent:  session.payment_intent ?? '',
        amount_total:    session.amount_total ?? 0,
      },
    };

    const ghResponse = await fetch(dispatchUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'Accept':        'application/vnd.github+json',
        'Content-Type':  'application/json',
        'User-Agent':    'nagoh-us-stripe-handler/1.0',
      },
      body: JSON.stringify(payload),
    });

    if (!ghResponse.ok) {
      const errorText = await ghResponse.text();
      console.error('GitHub dispatch failed', ghResponse.status, errorText);
      return new Response('Failed to trigger GitHub workflow', { status: 502 });
    }

    console.log(`Dispatched stripe-payment-success for @${githubUsername} → ${repoName}`);
    return new Response('OK', { status: 200 });
  },
};

// ── Stripe webhook signature verification ─────────────────────────────────────
//
// Uses the Web Crypto API (available in Cloudflare Workers) to compute HMAC-SHA256.
// Reference: https://stripe.com/docs/webhooks/signatures
//
async function verifyStripeSignature(payload, signatureHeader, secret) {
  // Parse the header: "t=<timestamp>,v1=<sig1>,v1=<sig2>,..."
  const parts = signatureHeader.split(',');
  const timestampPart = parts.find(p => p.startsWith('t='));
  const v1Sigs = parts.filter(p => p.startsWith('v1=')).map(p => p.slice(3));

  if (!timestampPart || v1Sigs.length === 0) {
    return false;
  }

  const timestamp = timestampPart.slice(2);

  // Reject events older than 5 minutes to prevent replay attacks.
  // We only check for stale (too-old) timestamps; future clock skew is allowed.
  const now = Math.floor(Date.now() / 1000);
  if (now - parseInt(timestamp, 10) > 300) {
    console.error('Stripe webhook timestamp is too old — possible replay attack');
    return false;
  }

  // signed_payload = "<timestamp>.<raw_body>"
  const signedPayload = `${timestamp}.${payload}`;

  // Import the webhook secret as an HMAC key
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );

  // Compute the expected signature
  const sigBytes = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(signedPayload));
  const expected = Array.from(new Uint8Array(sigBytes))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Constant-time string comparison — compares every character regardless of
  // where a mismatch occurs, preventing timing side-channel attacks.
  function timingSafeEqual(a, b) {
    const aLen = a.length;
    const bLen = b.length;
    const len  = Math.max(aLen, bLen);
    // XOR of lengths is non-zero if they differ
    let diff = aLen ^ bLen;
    for (let i = 0; i < len; i++) {
      // charCodeAt returns NaN for out-of-range indices; `|| 0` makes it 0
      diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
    }
    return diff === 0;
  }

  // Compare against each v1 signature without short-circuiting
  let matched = false;
  for (const sig of v1Sigs) {
    if (timingSafeEqual(sig, expected)) {
      matched = true;
    }
  }

  return matched;
}
