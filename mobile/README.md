# DebtOut para iPhone y Android

La misma app de la web, empaquetada con [Capacitor 8](https://capacitorjs.com) como app nativa para App Store y Google Play. Dentro del móvil la app no necesita internet: todo va incluido en la instalación.

Lo que la versión nativa añade a la web (código en `native/bridge.js`):

- **Avisos de pago de verdad**: una notificación a las 9:00 el día de cada pago, aunque la app esté cerrada. Se programan para los próximos 3 meses y se rehacen cada vez que cambias algo o vuelves a la app.
- **Copia del plan en el almacenamiento nativo**, que el sistema no borra cuando falta espacio (iOS sí puede borrar el de una web).
- **Copias de seguridad con el menú Compartir**: guardar en Archivos o Drive, o enviártela.
- **Botón Atrás de Android**: cierra la hoja abierta, vuelve un paso o va a Inicio; en Inicio, sale.
- **Premium por suscripción** (1 mes gratis y después 2,99 € al mes), cobrada por Apple y Google a través de [RevenueCat](https://www.revenuecat.com). El mes gratis lo controlan las tiendas: una vez por cuenta de Apple o de Google, aunque la persona cambie de correo o reinstale la app. No hace falta pedir correo ni crear cuentas.
- **Asistente con IA** para Premium: responde dudas sobre deudas y sobre la app y, si la persona lo activa, usa su plan. Funciona a través del servidor de `server/` (ver su README).
- Vibración al marcar pagos y cerrar el mes, pantalla de inicio y barra de estado con los colores de DebtOut.

Sin Premium, la app es gratis con 1 deuda y 1 meta. La web sigue siendo gratis aparte (con todo incluido mientras dure su beta).

## Qué necesitas

| Para | Necesitas |
| --- | --- |
| Generar la app | Node.js 22 o posterior y Python 3 |
| Android | [Android Studio](https://developer.android.com/studio) (cualquier sistema) y una cuenta de Google Play Console (25 $, pago único) |
| iPhone | Un Mac con Xcode 26 y una cuenta del Apple Developer Program (99 € al año) |

## Trabajar con la app

```bash
cd mobile
npm install          # solo la primera vez
npm run android      # genera la app, la copia al proyecto Android y abre Android Studio
npm run ios          # lo mismo con Xcode (solo en un Mac)
```

`npm run sync` hace lo mismo sin abrir nada. Ejecútalo cada vez que cambies `src/app.html`: `python3 src/build.py` genera `mobile/www` (la app sin service worker ni avisos de instalación) y `native.js` a partir de `native/bridge.js`; `cap sync` lo copia a los proyectos nativos.

Si cambias el logo: `npm run assets` vuelve a dibujar los iconos, el icono de notificación y las pantallas de inicio de los dos sistemas.

En Android Studio, el botón ▶ instala la app en el emulador o en tu móvil (con la depuración USB activada). En Xcode, elige tu equipo de desarrollo en *Signing & Capabilities* y pulsa ▶.

## Antes de publicar por primera vez

1. **El identificador de la app** es `es.debtout.app` (en `capacitor.config.json`, `android/app/build.gradle` y el proyecto de Xcode). Una vez publicada no se puede cambiar. Si prefieres otro (por ejemplo, con tu dominio al revés), cámbialo en esos tres sitios antes de la primera subida.
2. **Rellena `web/datos-titular.js`**: los textos legales de la app salen de ahí. Las tiendas revisan que la app tenga aviso legal y privacidad completos.
3. **Publica la web** (ver el README principal): las tiendas piden la dirección de la política de privacidad (`https://tu-dominio/privacidad/`) y una página de soporte (`https://tu-dominio/#preguntas` sirve, con el correo de contacto relleno).
4. **Revisa con un profesional los textos legales** (`src/legal_beta.html`). Ya incluyen un borrador de:
   - en la privacidad, el asistente de IA (qué se envía, a quién y con qué base legal), la suscripción, las notificaciones locales y las copias de iCloud o Google;
   - en los términos, las condiciones de Premium (precio, mes gratis, renovación, cancelación, reembolsos) y del asistente.

   Antes de publicar, confirma con un abogado o asesor el derecho de desistimiento, las transferencias internacionales y las condiciones de los proveedores (Anthropic, Cloudflare, RevenueCat), y firma con ellos sus contratos de encargo (DPA). Cuando elijas dónde alojar la web, cambia también la mención a Netlify.
5. **Configura la suscripción y el asistente** (apartados de abajo) y pon las claves en `src/build.py`.
6. **Sube la versión** en cada envío: `versionCode` y `versionName` en `android/app/build.gradle`; *Version* y *Build* en Xcode. Cada subida a una tienda necesita un número de compilación mayor que el anterior.

## Configurar la suscripción (1 mes gratis y 2,99 € al mes)

La app cobra Premium con las compras integradas de Apple y Google, que son obligatorias para suscripciones dentro de apps de las tiendas. RevenueCat (gratis hasta 2.500 $ de ingresos al mes) une las dos tiendas, dice a la app si la persona tiene Premium y se lo confirma al servidor del asistente.

1. **App Store Connect** (tu app > Suscripciones): crea un grupo de suscripciones «DebtOut Premium» y dentro una suscripción mensual, por ejemplo `premium_mensual`, a 2,99 €. Añádele una **oferta introductoria gratuita de 1 mes**. Apple solo se la da a quien no la haya usado antes en ese grupo.
2. **Play Console** (Monetizar > Suscripciones): crea la suscripción `premium_mensual` con un plan base mensual de 2,99 € y una **oferta de prueba gratuita de 1 mes** para clientes nuevos (que nunca hayan tenido esta suscripción). Google solo la ofrece a cuentas que puedan disfrutarla.
3. **RevenueCat**: crea un proyecto con una app de iOS y otra de Android (conectadas a App Store Connect y Play Console según sus instrucciones), un *entitlement* llamado `premium` con el producto `premium_mensual` de las dos tiendas y una *offering* `default` con un paquete mensual.
   El precio de las tiendas tiene que coincidir con `PREMIUM_PRICE` en `src/build.py`, que es el que aparece en la web, en los términos y en los textos de la app.
4. Copia las **claves públicas** de RevenueCat (`appl_…` y `goog_…`) en `REVENUECAT_IOS_KEY` y `REVENUECAT_ANDROID_KEY`, arriba de `src/build.py`, y la **clave secreta** (`sk_…`) al servidor del asistente (`server/README.md`).
5. Prueba la compra con un usuario de prueba (Sandbox en Apple, cuenta de pruebas de licencias en Google). En pruebas, el «mes» dura unos minutos.

La pantalla de Premium ya cumple lo que piden las tiendas para suscripciones: muestra el precio de la tienda, el mes gratis solo si esa cuenta puede tenerlo, la renovación automática, cómo cancelar, «Restaurar compras» y enlaces a los términos y a la privacidad.

## Configurar el asistente

Publica el servidor siguiendo `server/README.md` y pon su dirección en `AI_URL`, arriba de `src/build.py`. Luego `npm run sync`. Mientras `AI_URL` esté vacío, la app dice que el asistente aún no está disponible.

## Publicar en Google Play

1. En Android Studio: *Build > Generate Signed App Bundle*, crea una clave de firma y guárdala en un sitio seguro (sin ella no podrás actualizar la app). Sale un archivo `.aab`.
2. En [Play Console](https://play.google.com/console), crea la app, sube el `.aab` y rellena la ficha (textos de abajo).
3. **Cuentas personales nuevas**: Google exige una prueba cerrada con al menos 12 personas durante 14 días seguidos antes de poder publicar en producción. Invita a amigos o familia como testers.
4. Formularios que te pedirá:
   - *Seguridad de los datos*: el plan se queda en el móvil, pero con el asistente salen datos. Declara como **recogidos** (no compartidos: los tratan proveedores en tu nombre), opcionales, para *funcionalidad de la app*, cifrados en tránsito y sin guardar en tu servidor: *Información financiera* (las cifras del plan, solo si la persona activa «Usar mi plan»), *Mensajes en la app* u *otro contenido generado por el usuario* (las preguntas) e *Historial de compras* (estado de la suscripción, vía RevenueCat). Revisa las definiciones de Google al rellenarlo.
   - *Funciones financieras*: DebtOut es una herramienta de presupuesto personal; no ofrece préstamos, cuentas, pagos ni inversiones.
   - *Clasificación de contenido*: sin contenido sensible.
   - *Público objetivo*: mayores de 14 años, como dicen los términos.
   - *Permisos*: notificaciones (avisos de pago). La app no pide alarmas exactas.

## Publicar en App Store

1. En Xcode: elige *Any iOS Device*, luego *Product > Archive* y *Distribute App > App Store Connect*.
2. En [App Store Connect](https://appstoreconnect.apple.com), crea la app con el mismo identificador y rellena la ficha.
3. *Privacidad de la app*: declara *Información financiera* (cifras del plan, opcional), *Contenido del usuario* (preguntas al asistente) y *Compras* (estado de la suscripción), todo para *funcionalidad de la app*, **no vinculado** a la identidad de la persona y sin rastreo. Añade en la descripción o en los metadatos los enlaces a los términos (`https://tu-dominio/terminos/`) y a la privacidad, que Apple exige en apps con suscripción.
4. La app ya declara que no usa cifrado propio (`ITSAppUsesNonExemptEncryption`), así que Apple no preguntará por la exportación en cada versión.
5. Prueba antes con TestFlight: Apple la revisa en uno o dos días.

Apple rechaza las apps que son solo una web metida en una caja (norma 4.2). DebtOut funciona sin conexión y usa notificaciones, compartir, vibración y compras nativas, lo que ayuda; si te lo plantean en la revisión, explícalo en la respuesta. Para la revisión, Apple necesitará probar Premium: lo hará con su cuenta de Sandbox.

## Textos para las fichas

**Nombre** (máx. 30): DebtOut: sal de deudas

**Subtítulo de App Store** (máx. 30): Tu plan para cada mes

**Descripción breve de Google Play** (máx. 80): Reparte tu sueldo y mira en qué mes terminas de pagar tus deudas. Sin tu banco.

**Palabras clave de App Store** (máx. 100): deudas,presupuesto,ahorro,sueldo,préstamo,tarjeta,hipoteca,finanzas,pagos,metas

**Texto promocional** (máx. 170): Prueba Premium 1 mes gratis. Convierte tu sueldo en un plan y pregunta tus dudas al asistente con IA. Sin cuenta y sin conectar tu banco.

**Descripción**:

> DebtOut convierte tu sueldo en un plan para cada mes: qué pagar, qué guardar y cuánto te queda libre. Y te dice en qué mes terminarás de pagar tus deudas.
>
> CÓMO FUNCIONA
> 1. Pon tu sueldo: lo que te llega a la cuenta, cada mes o cada semana.
> 2. Apunta tus gastos fijos y tus deudas, con lo que debes, la TAE y la cuota mínima.
> 3. Reparte tu sueldo entre deudas, ahorro y dinero libre. DebtOut te propone un reparto y te avisa si no llega.
> 4. Sigue el plan: marca cada pago cuando lo hagas y cierra el mes.
>
> LO QUE TE DA
> • Tu fecha de salida: el mes en que terminas de pagar y cuánto te ahorras en intereses frente a pagar solo el mínimo.
> • Primero la deuda más cara: pagas el mínimo de todas y el extra va a la de interés más alto.
> • Calendario de pagos del mes, con avisos el día de cada pago.
> • Metas de ahorro: fondo de emergencia, un viaje, una mudanza.
> • Copias de seguridad para cambiar de móvil sin perder tu plan.
> • Asistente con IA: pregúntale qué deuda pagar antes, qué es la TAE o qué hacer si no llegas a fin de mes. Si quieres, responde con los números de tu plan.
>
> TUS DATOS SON TUYOS
> DebtOut no conecta con tu banco, no te pide cuenta ni contraseña y tu plan se guarda solo en tu móvil. Solo si tú lo activas, el asistente usa tus cifras (nunca tu nombre) para responderte. Sin anuncios, sin rastreadores.
>
> GRATIS O PREMIUM
> Úsala gratis con 1 deuda y 1 meta. Premium incluye deudas y metas ilimitadas, avisos de pago y el asistente con IA: 1 mes gratis y después 2,99 € al mes. La suscripción se renueva cada mes hasta que la canceles en los ajustes de tu cuenta, al menos 24 horas antes de la renovación.
>
> Términos: https://tu-dominio/terminos/ · Privacidad: https://tu-dominio/privacidad/
>
> DebtOut es una herramienta de planificación: sus cálculos y las respuestas del asistente son orientativos y no son asesoramiento financiero.

**Categoría**: Finanzas.

**Capturas**: `python3 src/make_screens.py` genera capturas de la app con datos de ejemplo en `web/screenshots` y `web/img`. Las tiendas piden tamaños concretos (por ejemplo 1320 × 2868 para iPhone de 6,9" y entre 320 y 3840 px para Android); la forma más fiel es hacerlas en el simulador de Xcode y en el emulador de Android Studio.
