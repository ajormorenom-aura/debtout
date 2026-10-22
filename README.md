# DebtOut

App web instalable (PWA) para repartir el sueldo entre gastos fijos, deudas, ahorro y dinero libre, y estimar cuándo terminarás de pagar tus deudas. No conecta con el banco ni mueve dinero.

Versión actual: **beta 0.9.0**. No hay cuentas ni pagos: el plan se guarda solo en el dispositivo de cada persona y las funciones Premium están incluidas gratis durante la beta.

## Qué hay en el repositorio

| Carpeta | Para qué |
| --- | --- |
| `web/` | La app lista para publicar. Netlify publica esta carpeta tal cual (ver `netlify.toml`). |
| `src/` | El código fuente y los scripts que generan `web/`. No se publica. |

Archivos de `web/` que conviene conocer:

- `datos-titular.js`: nombre, NIF, domicilio y correo del titular. Salen en el aviso legal, la privacidad y los términos. Se edita a mano y los scripts nunca lo sobrescriben.
- `sw.js`: service worker que guarda los archivos de la app para que abra sin conexión. No guarda datos personales.
- `_headers`: cabeceras de seguridad para Netlify.

## Publicar cambios

Cada cambio que llega a la rama `main` se publica solo en Netlify. Cada publicación gasta créditos del plan gratuito de Netlify, así que conviene juntar varios cambios en un solo envío.

Para cambiar la app:

1. Edita `src/app.html` (pantallas, estilos y lógica) o `src/legal_beta.html` (textos legales).
2. Genera `web/` con `python3 src/build.py`.
3. Prueba en local: `python3 src/serve.py` y abre http://127.0.0.1:8765, o ejecuta `python3 src/test_app.py` con el servidor en marcha (necesita Playwright y Chromium).
4. Sube los cambios a `main`.

Otros scripts de `src/`: `make_icons.py` (iconos), `make_fonts.py` (tipografía Inter en WOFF), `make_screens.py` (capturas para el instalador) y `build_preview.py` (vista previa para el visor de Claude).

## Licencias

La tipografía Inter se usa bajo la SIL Open Font License 1.1 (`web/fonts/OFL.txt`). El resto del código y los textos pertenecen al titular de DebtOut.
