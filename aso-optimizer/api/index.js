/**
 * aso-optimizer/api/index.js — Cloudflare Worker
 *
 * Routes:
 *   POST /api/lookup           — Fetch App Store metadata (iTunes API + HTML scrape)
 *   POST /api/optimize         — DeepSeek-V3 ASO optimization (market recs + localization)
 *   POST /api/create-checkout  — Create a Stripe Checkout session
 *   POST /api/verify-session   — Verify a completed Stripe Checkout session (stateless)
 *   POST /api/stripe/webhook   — Handle Stripe webhook events (signature verified)
 *
 * Required Cloudflare Worker Secrets (set via `wrangler secret put` or dashboard):
 *   DEEPSEEK_API_KEY       — DeepSeek API key (never exposed to the frontend)
 *   STRIPE_SECRET_KEY      — Stripe secret key (sk_live_... or sk_test_...)
 *   STRIPE_WEBHOOK_SECRET  — Stripe webhook signing secret (whsec_...)
 */

// ── CORS ─────────────────────────────────────────────────────────────────────

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}

function errorResponse(message, status = 400) {
  return jsonResponse({ error: message }, status);
}

// ── iTunes Lookup + HTML Scrape ───────────────────────────────────────────────

/**
 * Scrape the full app description from App Store HTML.
 *
 * Priority order:
 *   1. JSON-LD structured data (most reliable)
 *   2. og:description meta tag (usually truncated but better than nothing)
 */
function scrapeDescription(html) {
  // 1. JSON-LD (Apple embeds schema.org SoftwareApplication data)
  const ldMatches = html.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi);
  for (const m of ldMatches) {
    try {
      const ld = JSON.parse(m[1]);
      if (ld.description) return ld.description;
      if (Array.isArray(ld['@graph'])) {
        for (const node of ld['@graph']) {
          if (node.description) return node.description;
        }
      }
    } catch {
      // Malformed JSON — skip
    }
  }

  // 2. og:description
  const ogMatch = html.match(/<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']/i)
    ?? html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:description["']/i);
  if (ogMatch) return ogMatch[1];

  return null;
}

async function handleLookup(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return errorResponse('Request body must be valid JSON');
  }

  const { appUrl } = body ?? {};
  if (!appUrl || typeof appUrl !== 'string') {
    return errorResponse('appUrl is required');
  }

  // Extract numeric App ID: works for both storefront and direct URLs
  const idMatch = appUrl.match(/[?&/]id(\d+)/i) ?? appUrl.match(/\/id(\d+)/i);
  if (!idMatch) {
    return errorResponse('Could not extract an App ID from the provided URL. Make sure it is a valid App Store link (e.g. https://apps.apple.com/us/app/name/id123456789).');
  }
  const appId = idMatch[1];

  // Fetch iTunes lookup API and raw App Store HTML in parallel
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10_000);

  let lookupRes, htmlRes;
  try {
    [lookupRes, htmlRes] = await Promise.all([
      fetch(`https://itunes.apple.com/lookup?id=${appId}&country=us&entity=software`, {
        signal: controller.signal,
      }),
      fetch(appUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept': 'text/html,application/xhtml+xml',
        },
        signal: controller.signal,
      }),
    ]);
  } catch (err) {
    return errorResponse('Failed to reach Apple servers. Please try again.');
  } finally {
    clearTimeout(timeoutId);
  }

  if (!lookupRes.ok) {
    return errorResponse('Apple\'s lookup API returned an error. Please try again in a moment.');
  }

  let lookupData, html;
  try {
    [lookupData, html] = await Promise.all([
      lookupRes.json(),
      htmlRes.text(),
    ]);
  } catch (err) {
    console.error('Failed to parse Apple API response:', err);
    return errorResponse('Received an unexpected response from Apple. The App Store may be temporarily unavailable — please try again in a moment.');
  }

  if (!lookupData.results || lookupData.results.length === 0) {
    return errorResponse('App not found. Double-check the App Store URL and try again.', 404);
  }

  const app = lookupData.results[0];

  // Prefer scraped description (full) over API description (may be truncated)
  const fullDescription = scrapeDescription(html) || app.description || '';

  return jsonResponse({
    appId,
    name: app.trackName ?? '',
    subtitle: app.subtitle ?? '',
    description: fullDescription,
    category: app.primaryGenreName ?? '',
    primaryGenre: app.primaryGenreName ?? '',
    iconUrl: app.artworkUrl512 ?? app.artworkUrl100 ?? '',
    bundleId: app.bundleId ?? '',
    developer: app.artistName ?? '',
    rating: app.averageUserRating ?? null,
    ratingCount: app.userRatingCount ?? 0,
    price: app.price ?? 0,
    currency: app.currency ?? 'USD',
    minimumOsVersion: app.minimumOsVersion ?? '',
    releaseNotes: app.releaseNotes ?? '',
    version: app.version ?? '',
  });
}

// ── Market Recommendations ────────────────────────────────────────────────────

const MARKET_MAP = {
  Games: [
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Highest mobile game ARPU globally; RPG and puzzle genres dominate' },
    { market: 'South Korea', locale: 'ko', flag: '🇰🇷', reason: 'Top-tier gaming culture with strong esports adoption and high spend' },
    { market: 'China (Simplified)', locale: 'zh-Hans', flag: '🇨🇳', reason: 'Largest player base; mid-core and casual titles see massive scale' },
  ],
  Finance: [
    { market: 'Germany', locale: 'de', flag: '🇩🇪', reason: 'Privacy-first market with rising fintech adoption and high trust requirements' },
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Rapidly growing mobile banking segment and tech-savvy aging population' },
    { market: 'Brazil', locale: 'pt-BR', flag: '🇧🇷', reason: "Latin America's largest fintech market; Pix-driven mobile-first behavior" },
  ],
  'Health & Fitness': [
    { market: 'Germany', locale: 'de', flag: '🇩🇪', reason: 'Highest per-capita health app spend in Europe' },
    { market: 'Australia', locale: 'en-AU', flag: '🇦🇺', reason: 'Active lifestyle culture with strong Apple Watch penetration' },
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Wellness and longevity focus drives consistent in-app purchase revenue' },
  ],
  Productivity: [
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Productivity tool adoption is extremely high; users pay for quality' },
    { market: 'Germany', locale: 'de', flag: '🇩🇪', reason: 'Professional market values privacy and reliability — strong B2B opportunity' },
    { market: 'France', locale: 'fr', flag: '🇫🇷', reason: "Large App Store market with underserved French-language productivity tools" },
  ],
  Education: [
    { market: 'China (Simplified)', locale: 'zh-Hans', flag: '🇨🇳', reason: 'Education is a national priority; enormous demand for learning apps' },
    { market: 'South Korea', locale: 'ko', flag: '🇰🇷', reason: 'Intense academic culture drives sustained engagement with edu apps' },
    { market: 'Brazil', locale: 'pt-BR', flag: '🇧🇷', reason: 'Young population and mobile-first learning make LATAM a growth market' },
  ],
  'Food & Drink': [
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Food culture is central to daily life; delivery and recipe apps thrive' },
    { market: 'France', locale: 'fr', flag: '🇫🇷', reason: 'Culinary identity drives strong engagement with food apps' },
    { market: 'Brazil', locale: 'pt-BR', flag: '🇧🇷', reason: 'iFood ecosystem primed the market; food discovery apps see rapid growth' },
  ],
  Travel: [
    { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Outbound tourism is rebounding; travel utility apps see strong installs' },
    { market: 'Germany', locale: 'de', flag: '🇩🇪', reason: 'High travel frequency and disposable income make this a premium market' },
    { market: 'Brazil', locale: 'pt-BR', flag: '🇧🇷', reason: 'Growing middle class is fuelling a domestic tourism boom' },
  ],
};

const DEFAULT_MARKETS = [
  { market: 'Japan', locale: 'ja', flag: '🇯🇵', reason: 'Large App Store market with the highest per-user revenue in Asia' },
  { market: 'Germany', locale: 'de', flag: '🇩🇪', reason: 'Quality-focused European market with low churn and strong IAP revenue' },
  { market: 'Brazil', locale: 'pt-BR', flag: '🇧🇷', reason: 'Fast-growing market with an expanding mobile-first middle class' },
];

function getMarketRecommendations(primaryGenre) {
  for (const [key, markets] of Object.entries(MARKET_MAP)) {
    if (primaryGenre && primaryGenre.toLowerCase().includes(key.toLowerCase())) {
      return markets;
    }
  }
  return DEFAULT_MARKETS;
}

// ── DeepSeek ASO Prompt ───────────────────────────────────────────────────────

function buildASOPrompt(metadata, targetLocale, marketName) {
  return `You are a world-class App Store Optimization (ASO) specialist and professional localizer with deep knowledge of the ${marketName} market.

APP METADATA:
- Name: ${metadata.name}
- Current Subtitle: ${metadata.subtitle || '(none)'}
- Primary Genre: ${metadata.primaryGenre}
- Current Description (full):
${metadata.description}

TARGET MARKET: ${marketName} (locale: ${targetLocale})

YOUR TASKS:

TASK 1 — HIGH-ACCURACY LOCALIZATION (cultural adaptation, NOT literal translation):
- Adapt idioms, metaphors, and cultural references for ${marketName} audiences
- Use natural, market-appropriate language that native speakers expect
- Consider local user expectations, values, and terminology
- For Japanese: use appropriate keigo/teineigo register; avoid katakana overuse
- For Korean: use friendly but professional 합쇼체 register
- For German: use formal Sie; emphasize reliability, privacy, and precision
- For Portuguese (BR): use informal but enthusiastic tone; localize price references

TASK 2 — ASO KEYWORD OPTIMIZATION:
- Inject the most searchable keywords NATURALLY into the FIRST 3 LINES (the fold — visible before the user taps "More")
- Use short, scannable paragraphs (2-3 sentences max)
- Lead with the strongest value proposition
- Use bullet points (•) for feature lists
- End with a compelling, culturally appropriate call-to-action
- Title: max 30 characters (includes spaces)
- Subtitle: max 30 characters (includes spaces) — must contain the #1 keyword

Return ONLY a JSON object in this EXACT structure (no markdown, no commentary outside the JSON):
{
  "title": "Localized app name (max 30 chars)",
  "subtitle": "Keyword-rich subtitle (max 30 chars)",
  "description": "Full ASO-optimized localized description with fold-optimized first 3 lines",
  "keywords": "10-15 comma-separated App Store keyword suggestions in ${targetLocale}",
  "changes": "Brief English summary of key localization and ASO decisions made"
}`;
}

function parseAIResponse(content) {
  // Strip any markdown code fences if present
  const stripped = content.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/i, '').trim();
  const jsonMatch = stripped.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch {
      // Malformed JSON
    }
  }
  // Fallback: return raw text so the frontend can still display something
  return { raw: content, error: 'Could not parse structured AI response' };
}

// ── /api/optimize ─────────────────────────────────────────────────────────────

async function handleOptimize(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return errorResponse('Request body must be valid JSON');
  }

  const { metadata, targetLocale, marketName, sessionId } = body ?? {};

  if (!metadata || typeof metadata !== 'object') {
    return errorResponse('metadata object is required');
  }

  const markets = getMarketRecommendations(metadata.primaryGenre);

  // Free tier: return only market recommendations (no AI call)
  if (!sessionId) {
    return jsonResponse({ markets, premium: false });
  }

  // Premium tier: verify Stripe session before calling DeepSeek
  const stripeVerification = await verifyStripeSession(sessionId, env);
  if (!stripeVerification.paid) {
    return errorResponse('Payment not confirmed. Complete checkout before accessing premium results.', 402);
  }

  const locale = targetLocale || markets[0]?.locale || 'ja';
  const market = marketName || markets[0]?.market || 'Japan';

  // Call DeepSeek-V3
  let aiResponse;
  try {
    const deepseekRes = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.DEEPSEEK_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [
          {
            role: 'system',
            content: 'You are an expert App Store Optimization specialist and professional translator. Always return valid JSON only — no markdown, no extra text.',
          },
          {
            role: 'user',
            content: buildASOPrompt(metadata, locale, market),
          },
        ],
        temperature: 0.6,
        max_tokens: 2500,
        response_format: { type: 'json_object' },
      }),
    });

    if (!deepseekRes.ok) {
      const errText = await deepseekRes.text();
      console.error('DeepSeek API error:', deepseekRes.status, errText);
      return errorResponse('AI service unavailable. Please try again shortly.', 502);
    }

    aiResponse = await deepseekRes.json();
  } catch (err) {
    console.error('DeepSeek fetch error:', err);
    return errorResponse('Failed to reach AI service.', 502);
  }

  const aiContent = aiResponse.choices?.[0]?.message?.content ?? '';
  const optimized = parseAIResponse(aiContent);

  return jsonResponse({
    markets,
    targetLocale: locale,
    marketName: market,
    optimized,
    premium: true,
  });
}

// ── Stripe Session Verification ───────────────────────────────────────────────

async function verifyStripeSession(sessionId, env) {
  if (!sessionId || typeof sessionId !== 'string') return { paid: false };

  // Basic format guard: Stripe session IDs start with "cs_"
  if (!sessionId.startsWith('cs_')) return { paid: false };

  try {
    const res = await fetch(`https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(sessionId)}`, {
      headers: {
        'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
      },
    });

    if (!res.ok) return { paid: false };
    const session = await res.json();
    return { paid: session.payment_status === 'paid', session };
  } catch {
    return { paid: false };
  }
}

// ── /api/verify-session ───────────────────────────────────────────────────────

async function handleVerifySession(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return errorResponse('Request body must be valid JSON');
  }

  const { sessionId } = body ?? {};
  if (!sessionId) return errorResponse('sessionId is required');

  const result = await verifyStripeSession(sessionId, env);
  return jsonResponse({ paid: result.paid });
}

// ── /api/create-checkout ──────────────────────────────────────────────────────

async function handleCreateCheckout(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return errorResponse('Request body must be valid JSON');
  }

  const { appName, targetLocale, marketName, successUrl, cancelUrl } = body ?? {};
  if (!appName) return errorResponse('appName is required');

  const params = new URLSearchParams({
    mode: 'payment',
    'payment_method_types[]': 'card',
    'line_items[0][price_data][currency]': 'usd',
    'line_items[0][price_data][product_data][name]': `ASO Premium Report — ${appName}`,
    'line_items[0][price_data][product_data][description]': `AI-powered ASO optimization for ${marketName || 'top global markets'} (${targetLocale || 'multiple locales'})`,
    'line_items[0][price_data][unit_amount]': '2900', // $29.00
    'line_items[0][quantity]': '1',
    'success_url': successUrl || `https://nagoh.us/aso-optimizer/?session_id={CHECKOUT_SESSION_ID}&paid=true`,
    'cancel_url': cancelUrl || `https://nagoh.us/aso-optimizer/?cancelled=true`,
    'metadata[app_name]': appName,
    'metadata[target_locale]': targetLocale ?? '',
    'metadata[market_name]': marketName ?? '',
  });

  let stripeRes;
  try {
    stripeRes = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
    });
  } catch {
    return errorResponse('Failed to reach Stripe. Please try again.', 502);
  }

  const session = await stripeRes.json();
  if (session.error) {
    console.error('Stripe checkout error:', session.error);
    return errorResponse(session.error.message || 'Stripe error', 502);
  }

  return jsonResponse({ url: session.url, sessionId: session.id });
}

// ── /api/stripe/webhook ───────────────────────────────────────────────────────

async function handleStripeWebhook(request, env) {
  const rawBody = await request.text();
  const sigHeader = request.headers.get('stripe-signature');

  if (!sigHeader) {
    return new Response('Missing stripe-signature header', { status: 400 });
  }

  const isValid = await verifyStripeSignature(rawBody, sigHeader, env.STRIPE_WEBHOOK_SECRET);
  if (!isValid) {
    console.error('Stripe webhook signature verification failed');
    return new Response('Unauthorized', { status: 401 });
  }

  let event;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return new Response('Invalid JSON', { status: 400 });
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    console.log(`ASO checkout completed — session: ${session.id}, app: ${session.metadata?.app_name}`);
    // Stateless design: the frontend polls /api/verify-session to unlock premium content.
    // No database writes needed here.
  }

  return new Response('OK', { status: 200 });
}

// Maximum age (in seconds) for a Stripe webhook timestamp before it is
// rejected as a potential replay attack.
const STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300;

async function verifyStripeSignature(payload, signatureHeader, secret) {
  const parts = signatureHeader.split(',');
  const timestampPart = parts.find(p => p.startsWith('t='));
  const v1Sigs = parts.filter(p => p.startsWith('v1=')).map(p => p.slice(3));

  if (!timestampPart || v1Sigs.length === 0) return false;

  const timestamp = timestampPart.slice(2);
  const now = Math.floor(Date.now() / 1000);
  // Reject replays older than 5 minutes
  if (now - parseInt(timestamp, 10) > STRIPE_WEBHOOK_TOLERANCE_SECONDS) {
    console.error('Stripe webhook timestamp too old — possible replay attack');
    return false;
  }

  const signedPayload = `${timestamp}.${payload}`;
  const encoder = new TextEncoder();

  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );

  const sigBytes = await crypto.subtle.sign('HMAC', key, encoder.encode(signedPayload));
  const expected = Array.from(new Uint8Array(sigBytes))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Constant-time comparison to prevent timing attacks
  function timingSafeEqual(a, b) {
    const len = Math.max(a.length, b.length);
    let diff = a.length ^ b.length;
    for (let i = 0; i < len; i++) {
      diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
    }
    return diff === 0;
  }

  let matched = false;
  for (const sig of v1Sigs) {
    if (timingSafeEqual(sig, expected)) matched = true;
  }
  return matched;
}

// ── Main fetch handler ────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // All real routes require POST
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405, headers: CORS_HEADERS });
    }

    // Strip the /aso-optimizer prefix when routed via the custom-domain
    // Cloudflare route (nagoh.us/aso-optimizer/api/*).  Workers.dev URLs
    // have no such prefix, so this is a no-op in development.
    const pathname = url.pathname.replace(/^\/aso-optimizer/, '');

    switch (pathname) {
      case '/api/lookup':          return handleLookup(request);
      case '/api/optimize':        return handleOptimize(request, env);
      case '/api/create-checkout': return handleCreateCheckout(request, env);
      case '/api/verify-session':  return handleVerifySession(request, env);
      case '/api/stripe/webhook':  return handleStripeWebhook(request, env);
      default:                     return errorResponse('Not Found', 404);
    }
  },
};
