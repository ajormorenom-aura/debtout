# DebtOut

Reparte el sueldo entre gastos fijos, deudas, ahorro y dinero libre, y estima cuándo terminarás de pagar tus deudas. No conecta con el banco ni mueve dinero.

Versión actual: **beta 0.10.0**. No hay cuentas ni pagos: el plan se guarda solo en el dispositivo de cada persona y las funciones Premium están incluidas gratis durante la beta.

DebtOut tiene tres caras, hechas con el mismo código:

| Qué | Dónde | Para qué |
| --- | --- | --- |
| **Web promocional** | `/` (`web/index.html`) | Presenta la app: cómo funciona, calculadora de intereses, privacidad, precio y preguntas frecuentes. Incluye las páginas legales `/aviso-legal/`, `/privacidad/`, `/cookies/` y `/terminos/`. |
| **App web** | `/app/` (`web/app/`) | La app, instalable desde el navegador y con funcionamiento sin conexión. Quien la instaló antes de que existiera la web sigue entrando directo a la app. |
| **App para iPhone y Android** | `mobile/` | La misma app empaquetada con Capacitor para App Store y Google Play, con notificaciones de pago reales. Ver [`mobile/README.md`](mobile/README.md). |

## Qué hay en el repositorio

| Carpeta | Para qué |
| --- | --- |
| `web/` | Web y app web listas para publicar en cualquier alojamiento de webs estáticas, tal cual. |
| `mobile/` | Proyecto de Capacitor: `native/bridge.js` (puente con el móvil), `android/` y `ios/` (proyectos nativos). `mobile/www` se genera y no se sube. |
| `src/` | El código fuente y los scripts que generan `web/` y `mobile/www`. No se publica. |

Archivos de `src/`:

- `app.html`: la app (pantallas, estilos y lógica). Se usa en la web y en el móvil.
- `landing.html`: la página de inicio de la web.
- `legal_beta.html`: textos legales, compartidos por la app y la web.
- `build.py`: genera todo. Arriba tiene tres ajustes: `SITE_URL` (la dirección pública de la web; con ella se añaden enlaces canónicos, imágenes absolutas para las vistas previas en WhatsApp o redes y `sitemap.xml`) y `APP_STORE_URL` / `PLAY_STORE_URL` (cuando la app esté en las tiendas, la web enlaza a ellas en vez de decir «Próximamente»).

Archivos de `web/` que conviene conocer:

- `datos-titular.js`: nombre, NIF, domicilio y correo del titular. Salen en el aviso legal, la privacidad y los términos de la app y de la web, y el correo en el pie de la web. Se edita a mano y los scripts nunca lo sobrescriben (la app móvil se lleva una copia en cada `build.py`).
- `sw.js`: service worker que guarda los archivos de la app y de la portada para que abran sin conexión. No guarda datos personales.

## Cambiar la web y la app

1. Edita `src/app.html`, `src/landing.html` o `src/legal_beta.html`.
2. Genera todo con `python3 src/build.py`.
3. Prueba en local: `python3 src/serve.py` y abre http://127.0.0.1:8765 (web) o http://127.0.0.1:8765/app/ (app). Las pruebas automáticas: `python3 src/test_app.py` con el servidor en marcha (necesitan Playwright y Chromium).
4. Sube los cambios a GitHub.

Otros scripts de `src/`: `make_screens.py` (capturas de la app para el instalador, la web y la imagen de vista previa `web/img/og.png`), `make_icons.py` (iconos web), `make_native_assets.py` (iconos y pantallas de inicio de iPhone y Android), `make_fonts.py` (tipografía Inter en WOFF) y `build_preview.py` (vista previa para el visor de Claude).

## Publicar la web

`web/` es una web estática: se publica copiando la carpeta tal cual, sin compilar nada, en cualquier alojamiento de webs estáticas (por ejemplo GitHub Pages o Cloudflare Pages). El repositorio ya no trae configuración para ningún alojamiento. El que elijas tiene que:

- servir `web/` en la raíz de un dominio (la app, el service worker y la página de error cuentan con `/app/`, `/sw.js` y `/`);
- usar HTTPS (sin él no se puede instalar la app ni funciona sin conexión);
- mostrar `web/404.html` en las direcciones que no existen.

La política de seguridad (qué puede cargar cada página) va dentro de las propias páginas, así que funciona en cualquier alojamiento.

**Al cambiar de alojamiento, actualiza la política de privacidad** (`src/legal_beta.html`, apartado «Quién más puede tratar datos»): ahora nombra a Netlify como proveedor que aloja la app.

## Publicar la app en las tiendas

Todo el proceso, los requisitos y los textos para las fichas de App Store y Google Play están en [`mobile/README.md`](mobile/README.md).

## Licencias

La tipografía Inter se usa bajo la SIL Open Font License 1.1 (`web/fonts/OFL.txt`). Capacitor y sus plugins, bajo la licencia MIT. El resto del código y los textos pertenecen al titular de DebtOut.
