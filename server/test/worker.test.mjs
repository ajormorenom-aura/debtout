/* Tests for the assistant server, with Claude and RevenueCat replaced by fakes (no keys, no cost).
   Run: npm test (bundles src/ with the .md knowledge the same way Wrangler does). */
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
let createHandler, SYSTEM_PROMPT;

before(async () => {
  const out = path.join(mkdtempSync(path.join(tmpdir(), "debtout-worker-")), "worker.mjs");
  await build({ entryPoints: [path.join(here, "test-entry.js")], bundle: true, format: "esm", platform: "node", loader: { ".md": "text" }, outfile: out, logLevel: "error" });
  ({ createHandler, SYSTEM_PROMPT } = await import(pathToFileURL(out).href));
});

const USER = "$RCAnonymousID:0123456789abcdef0123456789abcdef";
const NOW = new Date("2026-10-28T10:00:00Z");

function kv() {
  const m = new Map();
  return { m, get: async (k) => (m.has(k) ? m.get(k) : null), put: async (k, v) => { m.set(k, v); } };
}

function env(extra) {
  return { ANTHROPIC_API_KEY: "test-key", REVENUECAT_SECRET_KEY: "rc-secret", USAGE: kv(), MONTHLY_LIMIT: "3", ...extra };
}

/* A fake network: RevenueCat says whether the user is Premium; Claude answers or refuses. */
function network({ premium = true, expires = "2026-11-28T10:00:00Z", answer = "Paga primero la tarjeta.", stop = "end_turn" } = {}) {
  const calls = { revenuecat: 0, claude: [] };
  const fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.startsWith("https://api.revenuecat.com/")) {
      calls.revenuecat++;
      assert.equal(new Headers(init.headers).get("Authorization"), "Bearer rc-secret");
      const ents = premium ? { premium: { expires_date: expires, grace_period_expires_date: null, product_identifier: "premium_mensual" } } : {};
      return new Response(JSON.stringify({ subscriber: { entitlements: ents } }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.startsWith("https://api.anthropic.com/v1/messages")) {
      const headers = new Headers(init.headers);
      calls.claude.push({ url, body: JSON.parse(init.body), beta: headers.get("anthropic-beta") });
      const content = stop === "refusal" ? [] : [{ type: "thinking", thinking: "", signature: "x" }, { type: "text", text: answer }];
      return new Response(JSON.stringify({ id: "msg_1", type: "message", role: "assistant", model: "claude-opus-5-5", content, stop_reason: stop, stop_sequence: null,
        usage: { input_tokens: 40, output_tokens: 20, cache_read_input_tokens: 3000, cache_creation_input_tokens: 0 } }), { status: 200, headers: { "Content-Type": "application/json", "request-id": "req_1" } });
    }
    throw new Error("unexpected fetch " + url);
  };
  return { fetch, calls };
}

function post(body, origin = "capacitor://localhost") {
  return new Request("https://asistente.example/v1/preguntar", { method: "POST", headers: { "Content-Type": "application/json", Origin: origin }, body: JSON.stringify(body) });
}

const ASK = { usuario: USER, mensajes: [{ rol: "usuario", texto: "¿Qué deuda pago primero?" }] };

test("answers a Premium user's question with the cached knowledge and a refusal fallback", async () => {
  const net = network();
  const e = env();
  const res = await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(ASK), e);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "capacitor://localhost");
  const data = await res.json();
  assert.deepEqual(data, { respuesta: "Paga primero la tarjeta.", quedan: 2, limite: 3 });
  const call = net.calls.claude[0];
  assert.equal(call.body.model, "claude-opus-5-5");
  assert.equal(call.body.fallbacks, "default");
  assert.match(call.beta, /server-side-fallback-2026-07-01/);
  assert.deepEqual(call.body.output_config, { effort: "low" });
  assert.equal(call.body.system[0].cache_control.type, "ephemeral");
  assert.equal(call.body.system[0].text, SYSTEM_PROMPT);
  assert.ok(SYSTEM_PROMPT.includes("Cerrar el mes") && SYSTEM_PROMPT.includes("024") && SYSTEM_PROMPT.includes("método avalancha"));
  assert.equal(call.body.temperature, undefined);
  assert.deepEqual(call.body.messages, [{ role: "user", content: "¿Qué deuda pago primero?" }]);
  assert.equal(e.USAGE.m.size, 2, "question counter and Premium cache");
  assert.ok([...e.USAGE.m.keys()].every((k) => !k.includes("RCAnonymousID")), "purchase ids are stored hashed");
});

test("sends the plan only when the app includes it, as data before the question", async () => {
  const net = network();
  const plan = { ingresos_mes: 1850, deudas: [{ tipo: "Tarjeta", pendiente: 3200, tae: 19.9, cuota_minima: 95 }] };
  const body = { ...ASK, mensajes: [{ rol: "usuario", texto: "Hola" }, { rol: "asistente", texto: "¡Hola!" }, { rol: "usuario", texto: "¿Cuándo termino?" }], plan };
  await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(body), env());
  const msgs = net.calls.claude[0].body.messages;
  assert.equal(msgs.length, 3);
  assert.equal(msgs[1].role, "assistant");
  assert.equal(msgs[1].content, "¡Hola!");
  assert.equal(msgs[2].content[0].text, "<plan_del_usuario>\n" + JSON.stringify(plan) + "\n</plan_del_usuario>");
  assert.equal(msgs[2].content[1].text, "¿Cuándo termino?");
});

test("refuses people without Premium and does not call Claude", async () => {
  const net = network({ premium: false });
  const res = await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(ASK), env());
  assert.equal(res.status, 402);
  assert.equal((await res.json()).error, "no_premium");
  assert.equal(net.calls.claude.length, 0);
});

test("an expired subscription is not Premium", async () => {
  const net = network({ expires: "2026-10-01T00:00:00Z" });
  const res = await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(ASK), env());
  assert.equal(res.status, 402);
});

test("reuses a recent Premium check and stops at the monthly limit", async () => {
  const net = network();
  const e = env();
  const h = createHandler({ fetch: net.fetch, now: () => NOW });
  for (let i = 0; i < 3; i++) assert.equal((await h.fetch(post(ASK), e)).status, 200);
  const res = await h.fetch(post(ASK), e);
  assert.equal(res.status, 429);
  assert.deepEqual(await res.json(), { error: "limit", limite: 3, renueva: "2026-11-01" });
  assert.equal(net.calls.revenuecat, 1);
  assert.equal(net.calls.claude.length, 3);
});

test("a refused question gets a kind answer and does not use up the quota", async () => {
  const net = network({ stop: "refusal" });
  const res = await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(ASK), env());
  const data = await res.json();
  assert.equal(res.status, 200);
  assert.equal(data.rechazada, true);
  assert.equal(data.quedan, 3);
});

test("Haiku is called without the fallback parameter (it has no server-side fallback)", async () => {
  const net = network();
  await createHandler({ fetch: net.fetch, now: () => NOW }).fetch(post(ASK), env({ AI_MODEL: "claude-haiku-5-5" }));
  const call = net.calls.claude[0];
  assert.equal(call.body.model, "claude-haiku-5-5");
  assert.equal(call.body.fallbacks, undefined);
  assert.ok(!String(call.beta || "").includes("server-side-fallback"));
});

test("rejects malformed or oversized requests before any network call", async () => {
  const net = network();
  const h = createHandler({ fetch: net.fetch, now: () => NOW });
  const cases = [
    [{ ...ASK, usuario: "otra-persona@example.com" }, 400],
    [{ ...ASK, mensajes: [] }, 400],
    [{ ...ASK, mensajes: [{ rol: "asistente", texto: "hola" }] }, 400],
    [{ ...ASK, mensajes: [{ rol: "usuario", texto: "x".repeat(1501) }] }, 400],
    [{ ...ASK, plan: "no es un objeto" }, 400],
  ];
  for (const [body, status] of cases) assert.equal((await h.fetch(post(body), env())).status, status, JSON.stringify(body).slice(0, 80));
  assert.equal(net.calls.revenuecat + net.calls.claude.length, 0);
});

test("missing secrets, unknown origins, preflight and health", async () => {
  const net = network();
  const h = createHandler({ fetch: net.fetch, now: () => NOW });
  assert.equal((await h.fetch(post(ASK), env({ ANTHROPIC_API_KEY: "" }))).status, 503);
  const other = await h.fetch(post(ASK, "https://evil.example"), env());
  assert.equal(other.headers.get("Access-Control-Allow-Origin"), null);
  const pre = await h.fetch(new Request("https://asistente.example/v1/preguntar", { method: "OPTIONS", headers: { Origin: "https://localhost" } }), env());
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get("Access-Control-Allow-Origin"), "https://localhost");
  assert.equal((await h.fetch(new Request("https://asistente.example/salud"), env())).status, 200);
});
