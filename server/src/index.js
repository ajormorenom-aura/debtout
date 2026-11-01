/* DebtOut assistant server (Cloudflare Worker).

   POST /v1/preguntar   { usuario, mensajes: [{ rol: "usuario" | "asistente", texto }], plan? }
     -> 200 { respuesta, quedan, limite }
   GET  /salud          -> 200 { ok: true }

   The phone app sends the anonymous purchase id that RevenueCat gives it (usuario). Before calling Claude the
   server checks with RevenueCat that this id has an active Premium subscription (the free month counts) and
   that it still has questions left this month. It never stores questions, answers or plans; the only things
   it keeps (in KV) are a per-month question counter and, for 10 minutes, whether a purchase id is Premium,
   both under a hash of the id. Secrets (Wrangler): ANTHROPIC_API_KEY, REVENUECAT_SECRET_KEY. */
import Anthropic from "@anthropic-ai/sdk";
import { SYSTEM_PROMPT } from "./prompt.js";

const MAX_BODY = 24000;      // bytes
const MAX_TEXT = 1500;       // characters per message
const MAX_TURNS = 12;        // messages of history sent to the model
const MAX_PLAN = 9000;       // characters of plan data
const ENTITLEMENT_TTL = 600; // seconds a positive Premium check is reused
const REVENUECAT_ID = /^\$RCAnonymousID:[0-9a-f]{32}$/;

class Problem extends Error {
  constructor(status, code, extra) { super(code); this.status = status; this.code = code; this.extra = extra || {}; }
}

function cors(request, env) {
  const origin = request.headers.get("Origin");
  const allowed = String(env.ALLOWED_ORIGINS || "capacitor://localhost,https://localhost").split(",").map((s) => s.trim());
  const h = { "Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400", Vary: "Origin" };
  if (origin && allowed.includes(origin)) h["Access-Control-Allow-Origin"] = origin;
  return h;
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}

async function hash(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 40);
}

function month(now) { return now.toISOString().slice(0, 7); }
function nextMonth(now) { return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1)).toISOString().slice(0, 10); }

/* Checks the request and turns it into Claude messages. Earlier answers go back as plain text. */
function readRequest(body) {
  if (!body || typeof body !== "object") throw new Problem(400, "bad_request");
  const user = body.usuario;
  if (typeof user !== "string" || !REVENUECAT_ID.test(user)) throw new Problem(400, "bad_user");
  const list = Array.isArray(body.mensajes) ? body.mensajes.slice(-MAX_TURNS) : [];
  const messages = [];
  for (const m of list) {
    const role = m && m.rol === "usuario" ? "user" : m && m.rol === "asistente" ? "assistant" : null;
    const text = m && typeof m.texto === "string" ? m.texto.trim() : "";
    if (!role || !text) throw new Problem(400, "bad_messages");
    if (text.length > MAX_TEXT) throw new Problem(400, "too_long");
    messages.push({ role, content: text });
  }
  while (messages.length && messages[0].role !== "user") messages.shift();
  if (!messages.length || messages[messages.length - 1].role !== "user") throw new Problem(400, "bad_messages");

  if (body.plan != null) {
    if (typeof body.plan !== "object" || Array.isArray(body.plan)) throw new Problem(400, "bad_plan");
    const plan = JSON.stringify(body.plan);
    if (plan.length > MAX_PLAN) throw new Problem(400, "plan_too_long");
    const last = messages[messages.length - 1];
    last.content = [
      { type: "text", text: "<plan_del_usuario>\n" + plan + "\n</plan_del_usuario>" },
      { type: "text", text: last.content },
    ];
  }
  return { user, messages };
}

/* Premium = an active "premium" entitlement in RevenueCat (a free trial is active too). */
async function isPremium(user, key, env, doFetch, now) {
  const cacheKey = "ent:" + key;
  const cached = Number(await env.USAGE.get(cacheKey));
  if (cached > now.getTime()) return true;
  const res = await doFetch("https://api.revenuecat.com/v1/subscribers/" + encodeURIComponent(user), {
    headers: { Authorization: "Bearer " + env.REVENUECAT_SECRET_KEY, Accept: "application/json" },
  });
  if (!res.ok) throw new Problem(503, "store_unavailable");
  const data = await res.json();
  const ent = data && data.subscriber && data.subscriber.entitlements && data.subscriber.entitlements[env.ENTITLEMENT || "premium"];
  if (!ent) return false;
  const ends = Math.max(ent.expires_date ? Date.parse(ent.expires_date) : Infinity, ent.grace_period_expires_date ? Date.parse(ent.grace_period_expires_date) : 0);
  if (!(ends > now.getTime())) return false;
  const until = Math.min(ends, now.getTime() + ENTITLEMENT_TTL * 1000);
  await env.USAGE.put(cacheKey, String(until), { expirationTtl: ENTITLEMENT_TTL });
  return true;
}

async function ask(env, doFetch, messages) {
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY, fetch: doFetch, maxRetries: 1, timeout: 50000 });
  const model = env.AI_MODEL || "claude-haiku-5-5";
  const params = {
    model,
    max_tokens: 4000,
    output_config: { effort: env.AI_EFFORT || "low" },
    system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
    messages,
  };
  /* If the model declines, the API retries on the model Anthropic recommends for that case. Haiku models have
     no server-side fallback, so they get a plain request (a declined question gets a kind answer below). */
  const response = /haiku/.test(model)
    ? await client.messages.create(params)
    : await client.beta.messages.create({ ...params, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" });
  if (response.stop_reason === "refusal") return { refused: true, text: "" };
  const text = response.content.filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
  if (!text) throw new Problem(502, "empty_answer");
  return { refused: false, text };
}

export function createHandler(deps = {}) {
  const doFetch = deps.fetch || ((input, init) => fetch(input, init));
  const clock = deps.now || (() => new Date());
  return {
    async fetch(request, env) {
      const headers = cors(request, env);
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
      const url = new URL(request.url);
      if (url.pathname === "/salud" && request.method === "GET") return json({ ok: true }, 200, headers);
      if (url.pathname !== "/v1/preguntar" || request.method !== "POST") return json({ error: "not_found" }, 404, headers);
      try {
        if (!env.ANTHROPIC_API_KEY || !env.REVENUECAT_SECRET_KEY || !env.USAGE) throw new Problem(503, "not_configured");
        const raw = await request.text();
        if (raw.length > MAX_BODY) throw new Problem(413, "too_large");
        let body = null;
        try { body = JSON.parse(raw); } catch (e) { throw new Problem(400, "bad_json"); }
        const { user, messages } = readRequest(body);

        const now = clock();
        const key = await hash(user);
        if (!(await isPremium(user, key, env, doFetch, now))) throw new Problem(402, "no_premium");

        const limit = Math.max(1, Number(env.MONTHLY_LIMIT) || 30);
        const usageKey = "use:" + key + ":" + month(now);
        const used = Number(await env.USAGE.get(usageKey)) || 0;
        if (used >= limit) throw new Problem(429, "limit", { limite: limit, renueva: nextMonth(now) });

        const answer = await ask(env, doFetch, messages);
        if (answer.refused) {
          return json({ respuesta: "Con eso no puedo ayudarte. Si tienes otra duda sobre tus deudas o sobre DebtOut, pregúntame.", quedan: limit - used, limite: limit, rechazada: true }, 200, headers);
        }
        await env.USAGE.put(usageKey, String(used + 1), { expirationTtl: 40 * 24 * 3600 });
        return json({ respuesta: answer.text, quedan: limit - used - 1, limite: limit }, 200, headers);
      } catch (err) {
        if (err instanceof Problem) return json({ error: err.code, ...err.extra }, err.status, headers);
        if (err instanceof Anthropic.RateLimitError) return json({ error: "busy" }, 503, headers);
        if (err instanceof Anthropic.APIError) { console.error("anthropic", err.status); return json({ error: "ai_error" }, 502, headers); }
        console.error("server", err && err.name);
        return json({ error: "server_error" }, 500, headers);
      }
    },
  };
}

export default createHandler();
