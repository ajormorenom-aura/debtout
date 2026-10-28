# DebtOut para iPhone y Android

La misma app de la web, empaquetada con [Capacitor 8](https://capacitorjs.com) como app nativa para App Store y Google Play. Dentro del móvil la app no necesita internet: todo va incluido en la instalación.

Lo que la versión nativa añade a la web (código en `native/bridge.js`):

- **Avisos de pago de verdad**: una notificación a las 9:00 el día de cada pago, aunque la app esté cerrada. Se programan para los próximos 3 meses y se rehacen cada vez que cambias algo o vuelves a la app.
- **Copia del plan en el almacenamiento nativo**, que el sistema no borra cuando falta espacio (iOS sí puede borrar el de una web).
- **Copias de seguridad con el menú Compartir**: guardar en Archivos o Drive, o enviártela.
- **Botón Atrás de Android**: cierra la hoja abierta, vuelve un paso o va a Inicio; en Inicio, sale.
- Vibración al marcar pagos y cerrar el mes, pantalla de inicio y barra de estado con los colores de DebtOut.

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
4. **Revisa los textos legales** (`src/legal_beta.html`) para la versión de las tiendas. Ahora hablan de la web; conviene que también digan:
   - que la app se descarga de App Store o Google Play y que Apple o Google tratan los datos de la descarga según sus propias políticas;
   - que los avisos de pago son notificaciones locales que el propio móvil programa (no salen del dispositivo) y que se pueden desactivar;
   - que iCloud o la copia de seguridad de Google pueden incluir los datos de la app en las copias del propio usuario, si las tiene activadas;
   - que Netlify solo interviene en la versión web.
5. **Sube la versión** en cada envío: `versionCode` y `versionName` en `android/app/build.gradle`; *Version* y *Build* en Xcode. Cada subida a una tienda necesita un número de compilación mayor que el anterior.

## Publicar en Google Play

1. En Android Studio: *Build > Generate Signed App Bundle*, crea una clave de firma y guárdala en un sitio seguro (sin ella no podrás actualizar la app). Sale un archivo `.aab`.
2. En [Play Console](https://play.google.com/console), crea la app, sube el `.aab` y rellena la ficha (textos de abajo).
3. **Cuentas personales nuevas**: Google exige una prueba cerrada con al menos 12 personas durante 14 días seguidos antes de poder publicar en producción. Invita a amigos o familia como testers.
4. Formularios que te pedirá:
   - *Seguridad de los datos*: la app **no recoge ni comparte datos**. Todo se queda en el móvil.
   - *Funciones financieras*: DebtOut es una herramienta de presupuesto personal; no ofrece préstamos, cuentas, pagos ni inversiones.
   - *Clasificación de contenido*: sin contenido sensible.
   - *Público objetivo*: mayores de 14 años, como dicen los términos.
   - *Permisos*: notificaciones (avisos de pago). La app no pide alarmas exactas.

## Publicar en App Store

1. En Xcode: elige *Any iOS Device*, luego *Product > Archive* y *Distribute App > App Store Connect*.
2. En [App Store Connect](https://appstoreconnect.apple.com), crea la app con el mismo identificador y rellena la ficha.
3. *Privacidad de la app*: **No se recopilan datos**.
4. La app ya declara que no usa cifrado propio (`ITSAppUsesNonExemptEncryption`), así que Apple no preguntará por la exportación en cada versión.
5. Prueba antes con TestFlight: Apple la revisa en uno o dos días.

Apple rechaza las apps que son solo una web metida en una caja (norma 4.2). DebtOut funciona sin conexión y usa notificaciones, compartir y vibración nativas, lo que ayuda; si te lo plantean en la revisión, explícalo en la respuesta.

## Textos para las fichas

**Nombre** (máx. 30): DebtOut: sal de deudas

**Subtítulo de App Store** (máx. 30): Tu plan para cada mes

**Descripción breve de Google Play** (máx. 80): Reparte tu sueldo y mira en qué mes terminas de pagar tus deudas. Sin tu banco.

**Palabras clave de App Store** (máx. 100): deudas,presupuesto,ahorro,sueldo,préstamo,tarjeta,hipoteca,finanzas,pagos,metas

**Texto promocional** (máx. 170): Gratis durante la beta, con todo incluido. Convierte tu sueldo en un plan: qué pagar, qué guardar y cuánto te queda libre. Sin cuenta y sin conectar tu banco.

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
>
> TUS DATOS SON TUYOS
> DebtOut no conecta con tu banco, no te pide cuenta ni contraseña y no envía tu plan a ningún servidor: se guarda solo en tu móvil. Sin anuncios, sin rastreadores.
>
> Gratis durante la beta, con todas las funciones. DebtOut es una herramienta de planificación: sus cálculos son orientativos y no son asesoramiento financiero.

**Categoría**: Finanzas.

**Capturas**: `python3 src/make_screens.py` genera capturas de la app con datos de ejemplo en `web/screenshots` y `web/img`. Las tiendas piden tamaños concretos (por ejemplo 1320 × 2868 para iPhone de 6,9" y entre 320 y 3840 px para Android); la forma más fiel es hacerlas en el simulador de Xcode y en el emulador de Android Studio.

## Si más adelante se cobra Premium

Dentro de una app de las tiendas, una suscripción como Premium tiene que cobrarse con la compra integrada de Apple y de Google (se quedan un 15 % en el programa para pequeños desarrolladores). Habrá que añadir un plugin de compras y adaptar los textos legales cuando llegue el momento.
