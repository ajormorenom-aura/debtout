# DebtOut: textos para el anuncio de venta / Sales listing copy

Textos listos para Microns.io, Flippa y Acquire.com, primero en español y después en inglés. Los datos que solo conoce el vendedor están entre corchetes, por ejemplo [PRECIO]: rellénalos antes de publicar.

> **Nota para el vendedor.** Los portales piden describir el estado real del proyecto: código, ingresos y usuarios. Este texto presenta DebtOut como lo que es: un proyecto terminado a nivel de código y listo para lanzar, que todavía no está publicado en las tiendas y no tiene ingresos. Si vendes con ingresos o usuarios, añade sus cifras verificables. No cambies «pre-revenue» por otra cosa sin datos que lo respalden: describir mal el estado de un proyecto es la causa más habitual de disputas y devoluciones en estos portales.

---

# 🇪🇸 Español

## Titular (máx. 80 caracteres)

**DebtOut: app de salir de deudas con IA, lista para lanzar (iOS, Android y web)**

Alternativas:
- Micro-SaaS de finanzas personales: suscripción, IA y web. Código completo
- App de deudas y ahorro con asistente IA (Claude) y suscripción RevenueCat

## Resumen corto (máx. 300 caracteres)

DebtOut ayuda a salir de deudas: reparte el sueldo, ordena los pagos y calcula el mes de salida. App para iPhone, Android y web, con Premium a 2,99 €/mes (1 mes gratis protegido por Apple/Google) y asistente con IA de coste casi nulo. Código completo, 155 tests automáticos.

## Descripción completa

### Qué es DebtOut

DebtOut es una app de finanzas personales para salir de deudas. La persona escribe su sueldo, sus gastos fijos y sus deudas (lo que debe, la TAE y la cuota mínima), y DebtOut:

- **reparte el sueldo** entre gastos fijos, pago de deudas, ahorro y dinero libre, y propone un reparto recomendado;
- **calcula el mes exacto en que terminará de pagar** con el método avalancha (el extra va siempre a la deuda más cara) y cuánto se ahorra en intereses frente a pagar solo el mínimo;
- **ordena los pagos del mes** en un calendario, con **avisos de pago** como notificaciones del móvil el día de cada pago;
- gestiona **metas de ahorro** (fondo de emergencia, viajes, mudanzas…) que se llenan en orden;
- incluye un **asistente financiero con IA** que responde dudas sobre deudas, ahorro y el uso de la app y, si la persona lo activa, contesta con los números de su propio plan.

Es privada por diseño: sin cuentas, sin conectar el banco y sin rastreadores. El plan se guarda solo en el dispositivo.

### Modelo de negocio

- **Freemium con suscripción.** Gratis con 1 deuda y 1 meta. **Premium por 2,99 €/mes** (IVA incluido) desbloquea deudas y metas ilimitadas, avisos de pago y el asistente con IA.
- **1 mes de prueba gratis** para nuevos suscriptores.
- **Margen estimado por suscriptor: unos 2,10 €/mes**, después del IVA español (21 %) y de la comisión del 15 % de las tiendas para pequeños desarrolladores. El coste de IA es casi nulo (abajo) y el servidor cabe en el plan gratuito de Cloudflare hasta cientos de preguntas al día.
- La **web promocional** incluye una calculadora interactiva de intereses, pensada para atraer tráfico de búsqueda («cuánto tardo en pagar mi tarjeta»).

### Protección anti-fraude del mes gratis

El mes gratis no depende de un correo electrónico, así que crear cuentas nuevas no sirve para repetirlo. Lo gestionan **Apple y Google**: la oferta introductoria se concede **una sola vez por cuenta de App Store o Google Play**, aunque la persona cambie de correo, reinstale la app o cambie de móvil. La app consulta a la tienda si esa cuenta todavía puede disfrutar la prueba y solo entonces la ofrece. Si no puede, muestra directamente el precio. No hay que pedir correo ni mantener una base de datos de usuarios.

### Arquitectura técnica

- **Un solo código para todo.** La app (JavaScript sin frameworks, unas 2.300 líneas) genera la versión web y las apps nativas con un script de compilación.
- **Apps nativas con Capacitor 8.** Android con target SDK 36 (Android 16) y mínimo SDK 24; iOS 15 o posterior con Swift Package Manager. Funciones nativas: notificaciones locales, compartir, almacenamiento nativo, vibración, botón Atrás de Android, iconos y pantallas de inicio.
- **Pagos nativos verificados con RevenueCat.** Usa StoreKit (Apple) y Google Play Billing con un único *entitlement* «premium». El servidor también verifica la suscripción en RevenueCat antes de cada pregunta a la IA: Premium no se puede desbloquear manipulando la app.
- **Servidor en Cloudflare Workers.** Sin servidores que mantener y con escalado automático. Guarda en Workers KV un contador de preguntas al mes por suscriptor (con el identificador cifrado) y no almacena conversaciones ni datos financieros.
- **IA con Anthropic Claude Haiku 5.5** mediante el SDK oficial:
  - **coste estimado por debajo de 0,03 $ por usuario y mes** con el límite configurable de 30 preguntas mensuales (estimación con las tarifas públicas de Anthropic de octubre de 2026);
  - las instrucciones y el conocimiento se cachean entre preguntas;
  - se puede cambiar a Claude Opus 5.5 con una línea de configuración.
- **Base de conocimiento editable.** Cuatro archivos Markdown en español (uso de la app, conceptos como TAE o revolving, estrategias para salir de deudas, qué hacer si no se llega a fin de mes). Para enseñar algo nuevo al asistente basta con editar texto, sin reentrenar.
- **Web y app web (PWA).** Instalable, funciona sin conexión, política de seguridad estricta, cero peticiones a terceros y sin cookies. La portada promocional incluye calculadora, preguntas frecuentes, páginas legales e imagen para redes sociales.
- **Privacidad.** Compartir el plan con la IA es opcional y pide consentimiento explícito. El nombre nunca se envía.

### Calidad y estado

- **Código 100 % terminado**, con documentación completa.
- **145 tests automáticos de extremo a extremo** de la web y la app (Playwright) y **10 tests del servidor**, todos pasando. Cubren onboarding, cálculos, pagos, compras y bloqueos de Premium, el asistente (consentimiento, límites, errores, contenido malicioso), el modo sin conexión, la seguridad y el diseño en móvil y tablet. Además, 7 comprobaciones específicas de iPhone.
- La APK de Android compila con todas las dependencias, incluidas las compras.
- Accesible (gestión de foco, botón Atrás del sistema), con diseño oscuro cuidado y pensado para móvil y tablet.

### Qué incluye la venta

- Todo el código fuente: app, web, servidor, proyectos nativos de Android e iOS y scripts de compilación y pruebas.
- Marca DebtOut, logotipo, iconos, capturas e imagen para redes sociales.
- Base de conocimiento del asistente.
- Borradores de textos legales en español (aviso legal, privacidad, cookies y términos, orientados a RGPD y LSSI).
- Guía de publicación en las tiendas con los textos de las fichas listos, y guía técnica de traspaso (`TRANSFER_GUIDE.md`).
- [Dominio: indica si se incluye y cuál, o bórralo]
- [Soporte tras la venta: por ejemplo, 30 días por correo]

### Estado real (transparencia)

- **Pre-revenue**: todavía no está publicada en App Store ni en Google Play y no tiene usuarios ni ingresos.
- El comprador necesita sus propias cuentas: Apple Developer (99 €/año), Google Play Console (25 $, pago único), RevenueCat (gratis hasta 2.500 $ de ingresos al mes), Anthropic (pago por uso) y Cloudflare (plan gratuito). La guía de traspaso explica cada paso.
- Las compras reales, el servidor con claves reales y la app en dispositivos físicos se prueban al configurar esas cuentas: los tests automáticos usan tiendas e IA simuladas. La versión de iOS se compila en un Mac con Xcode.
- Los textos legales son borradores: el comprador debe completarlos con sus datos y revisarlos con un profesional.
- App y contenidos en español: está pensada para España y se puede adaptar a Latinoamérica o traducir.

### Oportunidades de crecimiento

- Lanzarla en App Store y Google Play: los textos de las fichas están escritos.
- SEO con la calculadora de intereses y contenido sobre deudas en español.
- Traducirla al inglés o adaptarla a mercados latinoamericanos.
- Alianzas con asociaciones de consumidores, ONG de educación financiera o empresas (bienestar financiero de empleados).
- Plan anual o funciones Premium adicionales (informes, varias cuentas).

### Por qué se vende

[MOTIVO DE VENTA, por ejemplo: «Soy desarrollador y prefiero centrarme en otro proyecto; DebtOut merece alguien que lo lance y lo haga crecer».]

### Precio y traspaso

- Precio: [PRECIO]
- Traspaso: entrega del código (ZIP limpio o transferencia del repositorio de GitHub), de la marca y de los recursos gráficos. Guía técnica incluida.

---

# 🇬🇧 English

## Headline (max. 80 characters)

**DebtOut: AI-powered debt payoff app, launch-ready (iOS, Android and web)**

Alternatives:
- Personal finance micro-SaaS: subscriptions, AI assistant and web. Code-complete
- Debt & savings app with Claude AI assistant and RevenueCat subscriptions

## Short summary (max. 300 characters)

DebtOut helps people get out of debt: it splits their salary, orders their payments and calculates their debt-free date. iPhone, Android and web app with Premium at €2.99/month (1-month free trial protected by Apple/Google) and a near-zero-cost AI assistant. Code-complete, 155 automated tests.

## Full description

### What DebtOut is

DebtOut is a personal finance app for getting out of debt. Users enter their net salary, fixed expenses and debts (balance, APR and minimum payment), and DebtOut:

- **splits the salary** between fixed expenses, debt payments, savings and free money, and suggests a recommended split;
- **calculates the exact month they will be debt-free** using the avalanche method (extra money always goes to the most expensive debt), and how much interest they save compared with paying only the minimums;
- **organises the month's payments** in a calendar, with **payment reminders** delivered as phone notifications on each due date;
- manages **savings goals** (emergency fund, trips, moving house…) that fill up in order;
- includes an **AI financial assistant** that answers questions about debt, saving and using the app and, if the user opts in, answers with the numbers of their own plan.

Private by design: no accounts, no bank connection, no trackers. The plan is stored only on the user's device.

### Business model

- **Freemium subscription.** Free with 1 debt and 1 goal. **Premium at €2.99/month** (VAT included) unlocks unlimited debts and goals, payment reminders and the AI assistant.
- **1-month free trial** for new subscribers.
- **Estimated margin per subscriber: about €2.10/month**, after Spanish VAT (21 %) and the stores' 15 % small-business commission. AI cost is near zero (see below), and the server fits Cloudflare's free plan up to hundreds of questions per day.
- The **marketing website** includes an interactive interest calculator, built to attract search traffic ("how long will it take to pay off my credit card").

### Free-trial fraud protection

The free month is not tied to an email address, so creating new accounts doesn't get it again. **Apple and Google** handle it: the introductory offer is granted **once per App Store or Google Play account**, even if the user changes email, reinstalls the app or switches phones. The app asks the store whether that account is still eligible and only then offers the trial; otherwise it shows the regular price. No email collection, no user database.

### Technical architecture

- **One codebase for everything.** The app (framework-free JavaScript, about 2,300 lines) builds both the web version and the native apps through a build script.
- **Native apps with Capacitor 8.** Android with target SDK 36 (Android 16) and min SDK 24; iOS 15 or later with Swift Package Manager. Native features: local notifications, sharing, native storage, haptics, Android back button, icons and splash screens.
- **Native payments verified with RevenueCat.** Uses StoreKit (Apple) and Google Play Billing with a single "premium" entitlement. The server also verifies the subscription with RevenueCat before every AI question: Premium can't be unlocked by tampering with the app.
- **Cloudflare Workers backend.** Serverless with automatic scaling. It keeps a monthly question counter per subscriber in Workers KV (with the ID hashed) and stores no conversations or financial data.
- **AI with Anthropic Claude Haiku 5.5** through the official SDK:
  - **estimated cost below $0.03 per user per month** with the configurable limit of 30 questions a month (estimate based on Anthropic's public pricing as of October 2026);
  - instructions and knowledge are cached between questions;
  - one config line switches it to Claude Opus 5.5.
- **Editable knowledge base.** Four Markdown files in Spanish (app usage; concepts such as APR and revolving credit; debt payoff strategies; what to do when money runs short). Teaching the assistant something new means editing text, with no retraining.
- **Website and web app (PWA).** Installable, works offline, strict Content Security Policy, zero third-party requests and no cookies. The marketing homepage includes the calculator, an FAQ, legal pages and a social preview image.
- **Privacy.** Sharing the plan with the AI is opt-in and asks for explicit consent. The user's name is never sent.

### Quality and status

- **100 % code-complete**, fully documented.
- **145 end-to-end automated tests** of the website and app (Playwright) and **10 server tests**, all passing. They cover onboarding, calculations, payments, purchases and Premium locks, the AI assistant (consent, limits, errors, malicious content), offline mode, security, and phone and tablet layouts. Plus 7 iPhone-specific checks.
- The Android APK builds with every dependency, including in-app purchases.
- Accessible (focus management, system back button), with a polished dark design for phone and tablet.

### What's included

- Full source code: app, website, server, native Android and iOS projects, build and test scripts.
- DebtOut brand, logo, icons, screenshots and social preview image.
- AI assistant knowledge base.
- Draft legal texts in Spanish (legal notice, privacy, cookies and terms, written with GDPR and Spain's e-commerce law, the LSSI, in mind).
- Store publishing guide with ready-to-use listing copy, and a technical handover guide (`TRANSFER_GUIDE.md`).
- [Domain: state whether one is included and which, or remove this line]
- [Post-sale support: e.g. 30 days by email]

### Current status (full disclosure)

- **Pre-revenue**: not yet published on the App Store or Google Play; no users or revenue.
- The buyer needs their own accounts: Apple Developer ($99/year), Google Play Console ($25 one-off), RevenueCat (free up to $2,500 monthly revenue), Anthropic (pay as you go) and Cloudflare (free plan). The handover guide walks through each step.
- Real purchases, the live server with real keys and physical devices get tested while setting up those accounts: the automated tests use simulated stores and AI. The iOS build is compiled on a Mac with Xcode.
- The legal texts are drafts: the buyer must add their own details and have them reviewed by a professional.
- App and content are in Spanish, designed for Spain; easy to adapt to Latin America or translate.

### Growth opportunities

- Launch on the App Store and Google Play: the listing copy is already written.
- SEO with the interest calculator and Spanish-language debt content.
- Translate to English or adapt for Latin American markets.
- Partnerships with consumer associations, financial-education nonprofits or employers (employee financial wellbeing).
- Annual plan or extra Premium features (reports, multiple accounts).

### Why I'm selling

[REASON FOR SALE, e.g. "I'm a developer focusing on another project; DebtOut deserves an owner who will launch and grow it."]

### Price and handover

- Asking price: [PRICE]
- Handover: source code (clean ZIP or GitHub repository transfer), brand and graphic assets. Technical guide included.
