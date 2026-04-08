/**
 * aso-optimizer/api/index.js — Cloudflare Worker
 */

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

// -- Scraper and Helper Functions --

function scrapeDescription(html) {
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
    } catch {}
  }
  const ogMatch = html.match(/<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']/i)
    ?? html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:description["']/i);
  return ogMatch ? ogMatch[1] : null;
}

// -- Route Handlers --

async function handleLookup(request) {
  let body;
  try { body = await request.json(); } catch { return errorResponse('Request body must be valid JSON'); }
  const { appUrl } = body ?? {};
  if (!appUrl) return errorResponse('appUrl is required');
  const idMatch = appUrl.match(/[?&/]id(\d+)/i) ?? appUrl.match(/\/id(\d+)/i);
  if (!idMatch) return errorResponse('Invalid App Store link.');
  const appId = idMatch[1];

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const [lookupRes, htmlRes] = await Promise.all([
      fetch(`https://itunes.apple.com/lookup?id=${appId}&country=us&entity=software`, { signal: controller.signal }),
      fetch(appUrl, { 
        headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' },
        signal: controller.signal 
      }),
    ]);
    const lookupData = await lookupRes.json();
    const html = await htmlRes.text();
    if (!lookupData.results?.length) return errorResponse('App not found', 404);
    const app = lookupData.results[0];
    return jsonResponse({
      appId,
      name: app.trackName,
      subtitle: app.subtitle,
      description: scrapeDescription(html) || app.description,
      primaryGenre: app.primaryGenreName,
      iconUrl: app.artworkUrl512 || app.artworkUrl100,
      developer: app.artistName,
      version: app.version
    });
  } catch (err) {
    return errorResponse('Failed to reach Apple servers.');
  } finally {
    clearTimeout(timeoutId);
  }
}

// -- Placeholder functions for Stripe/DeepSeek (logic omitted for brevity, keep your original implementations) --
async function handleOptimize(request, env) { /* Use your existing logic here */ return jsonResponse({ markets: [] }); }
async function handleCreateCheckout(request, env) { /* Use your existing logic here */ return jsonResponse({ url: '' }); }

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS_HEADERS });
    if (request.method !== 'POST') return new Response('Method Not Allowed', { status: 405, headers: CORS_HEADERS });

    // This handles both nagoh.us/aso-optimizer/api/* and direct workers.dev access
    const pathname = url.pathname.replace(/^\/aso-optimizer/, '');

    switch (pathname) {
      case '/api/lookup':          return handleLookup(request);
      case '/api/optimize':        return handleOptimize(request, env);
      case '/api/create-checkout': return handleCreateCheckout(request, env);
      default:                     return errorResponse('Not Found', 404);
    }
  },
};
