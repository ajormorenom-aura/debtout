# Guía de traspaso de DebtOut

Guía paso a paso para quien compra DebtOut: cómo tomar el control del código, desplegar el servidor en Cloudflare y conectar sus propias claves (Anthropic, RevenueCat, Google Play Console y App Store Connect). Al terminar tendrás la web publicada, el asistente funcionando y las apps listas para enviarse a las tiendas.

Los pasos de cada parte también están en los README del proyecto (`README.md`, `mobile/README.md` y `server/README.md`). Esta guía los ordena para el traspaso.

---

## 0. Qué recibes

| Carpeta | Qué es |
| --- | --- |
| `src/` | Código fuente: la app (`app.html`), la portada (`landing.html`), los textos legales (`legal_beta.html`), el script de compilación (`build.py`), las pruebas y los generadores de iconos y capturas. |
| `web/` | La web y la app web ya generadas, listas para publicar en cualquier alojamiento estático. |
| `mobile/` | Proyecto de Capacitor 8: puente nativo (`native/bridge.js`) y proyectos de Android (`android/`) e iOS (`ios/`). |
| `server/` | Servidor del asistente de IA (Cloudflare Workers), su base de conocimiento (`conocimiento/`) y sus pruebas. |
| `venta/` | Esta guía, los textos del anuncio y el script que genera el ZIP. |

**No incluye** cuentas, claves ni contraseñas: el código no contiene ningún secreto. Todas las cuentas de abajo se crean a tu nombre.

---

## 1. Requisitos

**Software**

| Para | Necesitas |
| --- | --- |
| Compilar la web y la app | Python 3.10 o posterior y Node.js 22 o posterior |
| Pruebas automáticas | `pip install playwright` y `python -m playwright install chromium` |
| App de Android | Android Studio (Windows, Mac o Linux) |
| App de iPhone | Un Mac con Xcode 26 |

**Cuentas** (todas a tu nombre)

| Servicio | Para qué | Coste |
| --- | --- | --- |
| [Cloudflare](https://dash.cloudflare.com/sign-up) | Servidor del asistente y, si quieres, la web | Plan gratuito |
| [Anthropic](https://console.anthropic.com) | La IA del asistente (Claude Haiku 5.5) | Pago por uso: menos de 0,03 $ por suscriptor y mes con el límite de 30 preguntas |
| [RevenueCat](https://www.revenuecat.com) | Une las compras de Apple y Google y verifica las suscripciones | Gratis hasta 2.500 $ de ingresos al mes |
| [Google Play Console](https://play.google.com/console) | Publicar en Android y cobrar | 25 $, pago único |
| [Apple Developer Program](https://developer.apple.com/programs/) | Publicar en iPhone y cobrar | 99 € al año |

---

## 2. Tomar el control del código

### 2.1. Recibir el código

- **Opción A, archivo ZIP** (`debtout-proyecto-venta.zip`). Descomprímelo y crea tu propio repositorio:

  ```bash
  cd debtout
  git init
  git add .
  git commit -m "DebtOut: código recibido en el traspaso"
  git branch -M main
  git remote add origin https://github.com/TU-USUARIO/debtout.git
  git push -u origin main
  ```

- **Opción B, transferencia del repositorio de GitHub.** El vendedor lo transfiere desde *Settings > General > Transfer ownership* y tú aceptas la invitación. Así recibes también el historial. Los commits antiguos conservan el nombre y el correo del vendedor.

### 2.2. Instalar y comprobar que todo funciona

```bash
# dependencias
(cd mobile && npm install)
(cd server && npm install)
pip install playwright && python -m playwright install chromium

# compilar web, app web y app móvil
python3 src/build.py

# pruebas del servidor: deben salir 10 de 10
(cd server && npm test)

# pruebas de la app: deja el servidor local en marcha en otra terminal
python3 src/serve.py
python3 src/test_app.py        # deben salir 145 de 145
```

Si las dos baterías de pruebas pasan, has recibido el proyecto completo y en buen estado.

---

## 3. Poner tus datos y tu identidad

### 3.1. Datos del titular

Edita `web/datos-titular.js` con tu nombre o razón social, NIF, domicilio y correo de contacto. Salen en el aviso legal, la privacidad y los términos. Con el correo relleno aparecen también el botón «Enviar comentarios» en la app y tu correo en el pie de la web.

### 3.2. Identificador de la app

Ahora es `es.debtout.app`. La app nunca se ha publicado, así que puedes elegir el tuyo, normalmente tu dominio al revés (por ejemplo, `com.tuempresa.debtout`). **Elígelo antes de la primera subida a las tiendas: después no se puede cambiar.** Hay que cambiarlo en:

1. `mobile/capacitor.config.json`: `appId`.
2. `mobile/android/app/build.gradle`: `namespace` y `applicationId`.
3. `mobile/android/app/src/main/java/es/debtout/app/MainActivity.java`: mueve el archivo a la carpeta del nuevo paquete (por ejemplo `java/com/tuempresa/debtout/`) y cambia su primera línea, `package es.debtout.app;`.
4. `mobile/android/app/src/main/res/values/strings.xml`: `package_name` y `custom_url_scheme`.
5. En Xcode: objetivo *App* > *Signing & Capabilities* > *Bundle Identifier* (es `PRODUCT_BUNDLE_IDENTIFIER` en `mobile/ios/App/App.xcodeproj/project.pbxproj`).

Después ejecuta `cd mobile && npm run sync`.

### 3.3. Ajustes de `src/build.py`

Arriba del archivo están todos los ajustes del negocio:

| Ajuste | Qué hace |
| --- | --- |
| `SITE_URL` | Dirección pública de la web (por ejemplo `https://debtout.es`). Activa los enlaces canónicos, el `sitemap.xml` y las imágenes absolutas para las vistas previas. |
| `PREMIUM_PRICE` | Precio mensual que muestran la app, la web y los términos (`"2,99 €"`). Debe coincidir con el que configures en las tiendas. |
| `REVENUECAT_IOS_KEY`, `REVENUECAT_ANDROID_KEY` | Claves públicas de RevenueCat (paso 6). |
| `AI_URL` | Dirección de tu servidor del asistente (paso 4). |
| `APP_STORE_URL`, `PLAY_STORE_URL` | Enlaces a las fichas de las tiendas, cuando estén publicadas. La web cambia «Próximamente» por enlaces de descarga. |
| `WEB_BETA_END` | Fecha de fin de la beta gratuita de la web, si quieres terminarla (con un mes de aviso, como dicen los términos). |

Tras cambiar cualquier ajuste: `python3 src/build.py` y, para el móvil, `cd mobile && npm run sync`.

---

## 4. Desplegar el servidor del asistente en Cloudflare

```bash
cd server
npx wrangler login                          # entra con tu cuenta de Cloudflare
npx wrangler kv namespace create USAGE      # copia el "id" que aparece
```

Pega ese id en `server/wrangler.toml`, en la línea `id = "PEGA_AQUI_EL_ID_DEL_KV"`. Después:

```bash
npx wrangler secret put ANTHROPIC_API_KEY       # tu clave de Anthropic (paso 5)
npx wrangler secret put REVENUECAT_SECRET_KEY   # tu clave secreta de RevenueCat, empieza por sk_ (paso 6)
npx wrangler deploy
```

Wrangler muestra la dirección del servidor, por ejemplo `https://debtout-asistente.tu-cuenta.workers.dev`. Comprueba que responde:

```bash
curl https://debtout-asistente.tu-cuenta.workers.dev/salud      # {"ok":true}
```

Pon esa dirección en `AI_URL` de `src/build.py`.

Ajustes del servidor (`server/wrangler.toml`; tras cambiarlos, `npx wrangler deploy`):

| Ajuste | Ahora | Qué hace |
| --- | --- | --- |
| `AI_MODEL` | `claude-haiku-5-5` | Modelo de Claude. `claude-opus-5-5` da respuestas de más calidad, a unos 0,60 $ por suscriptor y mes. |
| `AI_EFFORT` | `low` | Cuánto «piensa» antes de responder. |
| `MONTHLY_LIMIT` | `30` | Preguntas al mes por suscriptor. |
| `ALLOWED_ORIGINS` | `capacitor://localhost,https://localhost` | Orígenes de la app nativa en iPhone y Android. No hace falta cambiarlo. |

El plan gratuito de Workers KV tiene un límite diario de escrituras (1.000 cuando se escribió esta guía) y cada pregunta hace al menos una. Con más tráfico, el plan Workers Paid (5 $/mes) lo amplía.

---

## 5. Conectar Anthropic (la IA)

1. Crea una cuenta en [console.anthropic.com](https://console.anthropic.com), añade un método de pago y crea una clave de API.
2. Guárdala en el servidor: `npx wrangler secret put ANTHROPIC_API_KEY` (paso 4). Nunca la pongas en el código ni en la app.
3. **Pon un límite de gasto mensual** en la consola de Anthropic: si algo fallara, no pagarías más de lo que decidas.
4. Para enseñarle cosas nuevas al asistente, edita los archivos de `server/conocimiento/` (y lista los nuevos en `server/src/prompt.js`), ejecuta `npm test` y `npx wrangler deploy`. Más detalles en `server/README.md`.

---

## 6. Conectar las suscripciones: App Store Connect, Google Play Console y RevenueCat

Premium cuesta 2,99 €/mes con 1 mes gratis. El mes gratis lo controlan Apple y Google: una vez por cuenta de la tienda.

1. **App Store Connect** (tu app > *Suscripciones*): crea un grupo «DebtOut Premium» y, dentro, una suscripción mensual `premium_mensual` a 2,99 €, con una **oferta introductoria gratuita de 1 mes**.
2. **Google Play Console** (*Monetizar > Suscripciones*): crea la suscripción `premium_mensual` con un plan base mensual de 2,99 € y una **oferta de prueba gratuita de 1 mes** para clientes nuevos.
3. **RevenueCat**:
   - crea un proyecto con una app de iOS y otra de Android y conéctalas a cada tienda siguiendo las guías de RevenueCat (en Google, con una cuenta de servicio de Google Cloud con acceso a la API de Google Play; en Apple, con la clave de compras dentro de la app de App Store Connect);
   - crea un *entitlement* llamado exactamente `premium` y asígnale el producto `premium_mensual` de las dos tiendas;
   - crea una *offering* `default` con un paquete mensual.
4. **Claves**:
   - las públicas (`appl_…` para iOS y `goog_…` para Android) van en `REVENUECAT_IOS_KEY` y `REVENUECAT_ANDROID_KEY` de `src/build.py`;
   - la secreta (`sk_…`) va en el servidor: `npx wrangler secret put REVENUECAT_SECRET_KEY`.
5. `python3 src/build.py && cd mobile && npm run sync`.
6. Prueba la compra con usuarios de prueba (*Sandbox* en Apple, *testers de licencias* en Google). En pruebas, el «mes» dura unos minutos.

---

## 7. Compilar y publicar las apps

Instrucciones completas, formularios de privacidad y textos de las fichas en `mobile/README.md`. Resumen:

- **Android**: `cd mobile && npm run android` abre Android Studio. *Build > Generate Signed App Bundle* crea el `.aab` firmado. **Guarda la clave de firma en un sitio seguro**: sin ella no podrás actualizar la app. En Play Console, las cuentas personales nuevas deben hacer una prueba cerrada con al menos 12 testers durante 14 días antes de publicar.
- **iPhone** (en un Mac): `cd mobile && npm run ios` abre Xcode. Elige tu equipo en *Signing & Capabilities*, luego *Product > Archive* y súbelo a App Store Connect. Prueba con TestFlight antes de enviarlo a revisión.
- Sube los números de versión en cada envío (`versionCode` y `versionName` en `mobile/android/app/build.gradle`; *Version* y *Build* en Xcode).

---

## 8. Publicar la web

La carpeta `web/` se publica tal cual, sin compilar, en un alojamiento estático con HTTPS y en la raíz de un dominio. Con la misma cuenta de Cloudflare:

```bash
npx wrangler pages deploy web --project-name debtout
```

También puedes conectar tu repositorio de GitHub a Cloudflare Pages con el directorio de salida `web` y sin comando de compilación. Después añade tu dominio, ponlo en `SITE_URL` de `src/build.py`, vuelve a compilar y publica de nuevo.

---

## 9. Textos legales

Los textos de `src/legal_beta.html` son **borradores**:

1. Completa tus datos en `web/datos-titular.js` (paso 3.1).
2. En la política de privacidad, cambia la mención a Netlify por tu alojamiento real (por ejemplo, Cloudflare) y revisa la lista de proveedores (Anthropic, Cloudflare, RevenueCat).
3. Firma con cada proveedor su contrato de encargo del tratamiento (DPA), que todos ofrecen desde su panel o su web.
4. **Haz que los revise un profesional** antes de publicar en las tiendas, en especial el derecho de desistimiento y las transferencias internacionales.

Tras cambiarlos: `python3 src/build.py`.

---

## 10. Comprobación final

- [ ] `npm test` en `server/` (10 de 10) y `python3 src/test_app.py` (145 de 145) pasan.
- [ ] `web/datos-titular.js` tiene tus datos y el identificador de la app es el tuyo.
- [ ] El servidor responde en `/salud`, tiene sus dos secretos y `AI_URL` apunta a él.
- [ ] Anthropic tiene un límite de gasto mensual.
- [ ] Suscripción `premium_mensual` (2,99 €, 1 mes gratis) creada en las dos tiendas, *entitlement* `premium` y *offering* `default` en RevenueCat, claves en `src/build.py` y en el servidor.
- [ ] Una compra de prueba en cada tienda activa Premium y el asistente responde.
- [ ] La web está publicada en tu dominio y `SITE_URL` apunta a él.
- [ ] Textos legales completados y revisados.
- [ ] Clave de firma de Android guardada a buen recaudo.

---

## 11. Mantenimiento

| Para cambiar | Dónde |
| --- | --- |
| Pantallas, textos y lógica de la app | `src/app.html` → `python3 src/build.py` → `cd mobile && npm run sync` |
| Portada de la web | `src/landing.html` → `python3 src/build.py` |
| Precio que se muestra | `PREMIUM_PRICE` en `src/build.py` (y el precio en las tiendas) |
| Lo que sabe el asistente | `server/conocimiento/*.md` → `npx wrangler deploy` |
| Modelo de IA o límite de preguntas | `server/wrangler.toml` → `npx wrangler deploy` |
| Iconos y pantallas de inicio | `src/make_icons.py` y `npm run assets` en `mobile/` |
| Capturas de la app | `python3 src/make_screens.py` con el servidor local en marcha |

Antes de publicar cualquier cambio, ejecuta las dos baterías de pruebas. Revisa de vez en cuando las actualizaciones de las dependencias (`npm outdated` y `npm audit` en `mobile/` y `server/`).
