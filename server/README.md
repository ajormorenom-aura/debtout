# Asistente de IA de DebtOut (servidor)

Un servidor pequeño en Cloudflare Workers entre la app y Claude, la IA de Anthropic. Existe por tres motivos:

- La clave de la IA no puede ir dentro de la app: cualquiera podría sacarla y gastar a tu costa.
- Comprueba con RevenueCat que quien pregunta tiene Premium activo (el mes gratis cuenta).
- Limita las preguntas al mes por persona, para que el coste esté controlado.

No guarda preguntas, respuestas ni planes. Lo único que guarda son un contador de preguntas por mes y, durante 10 minutos, si un identificador de compra es Premium. Los dos se guardan con el identificador cifrado (hash).

## Publicarlo

Necesitas:
- una cuenta de [Cloudflare](https://dash.cloudflare.com/sign-up) (el plan gratuito basta);
- una clave de la API de Anthropic, creada en [console.anthropic.com](https://console.anthropic.com);
- RevenueCat configurado (ver `mobile/README.md`), con su clave secreta.

```bash
cd server
npm install
npx wrangler login                         # abre el navegador para entrar en Cloudflare
npx wrangler kv namespace create USAGE     # copia el "id" que sale y pégalo en wrangler.toml
npx wrangler secret put ANTHROPIC_API_KEY      # pega la clave de Anthropic
npx wrangler secret put REVENUECAT_SECRET_KEY  # pega la clave secreta de RevenueCat (empieza por sk_)
npx wrangler deploy
```

Al terminar, Wrangler muestra la dirección del servidor, por ejemplo `https://debtout-asistente.tu-cuenta.workers.dev`. Ponla en `AI_URL`, arriba de `src/build.py`, y vuelve a generar la app (`cd mobile && npm run sync`).

**Pon un límite de gasto mensual en la consola de Anthropic**, en su apartado de límites: si algo fallara, no pagarías más de lo que decidas.

## Enseñarle cosas («entrenarlo»)

El asistente no se reentrena. Antes de cada respuesta lee las instrucciones de `src/prompt.js` y la base de conocimiento de la carpeta `conocimiento/`, y responde con eso más lo que ya sabe. Para que sepa algo nuevo:

1. Edita el archivo que toque de `conocimiento/` o crea otro (`05-lo-que-sea.md`) y añádelo a la lista de `src/prompt.js`.
2. Escribe frases claras y concretas, como se lo explicarías a una persona. Si algo de la app cambia, cámbialo aquí también: el asistente no ve la app.
3. `npm test` para comprobar que todo sigue bien y `npx wrangler deploy` para publicarlo.

Lo que más ayuda es ir apuntando las dudas reales que te llegan, con su respuesta correcta.

## Ajustes (`wrangler.toml`)

| Ajuste | Qué hace | Ahora |
| --- | --- | --- |
| `AI_MODEL` | Modelo de Claude | `claude-haiku-5-5` |
| `AI_EFFORT` | Cuánto «piensa» antes de responder (`low`, `medium`, `high`) | `low` |
| `MONTHLY_LIMIT` | Preguntas al mes por persona | `30` |

Tras cambiarlos: `npx wrangler deploy`.

### Cuánto cuesta cada pregunta

Estimación con unos 4.800 tokens de instrucciones y conocimiento, respuestas cortas y el esfuerzo en `low`. La primera pregunta de una conversación paga el conocimiento entero. Las siguientes, si llegan en menos de 5 minutos, lo leen de la caché a una fracción del precio.

| Modelo | Primera pregunta | Siguientes | 30 preguntas al mes |
| --- | --- | --- | --- |
| Claude Haiku 5.5 (`claude-haiku-5-5`, **el que está puesto**) | unos 0,001 $ | menos de 0,001 $ | menos de 0,03 $ |
| Claude Opus 5.5 (`claude-opus-5-5`, el más capaz) | unos 0,03 $ | unos 0,013 $ | unos 0,60 $ |

Cada suscripción de 2,99 € deja unos 2,10 €, después de quitar el IVA y la comisión del 15 % de las tiendas para pequeños desarrolladores. Con Haiku, el asistente apenas consume margen aunque alguien agote las 30 preguntas. Si un día quieres respuestas de más calidad, cambia `AI_MODEL` a `claude-opus-5-5`: el código le añade solo el reintento con otro modelo cuando una pregunta es rechazada, porque Haiku no lo tiene.

Con un modelo tan barato puedes subir `MONTHLY_LIMIT` sin que el coste se note.

## Pruebas

`npm test` prueba el servidor sin claves ni gasto: Claude y RevenueCat se sustituyen por imitaciones. Comprueba qué se envía a la IA, el control de Premium, el límite mensual y los errores.

Para probar la versión real en tu ordenador: crea un archivo `.dev.vars` con `ANTHROPIC_API_KEY=...` y `REVENUECAT_SECRET_KEY=...` (no se sube a GitHub) y ejecuta `npx wrangler dev`.
