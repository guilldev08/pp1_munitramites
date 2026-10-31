# Contexto del proyecto — Munitramites

Memoria de trabajo para nuevos chats de OpenCode. Leer esto antes de tocar
código. El proyecto es un portal de trámites de Misiones (Django + Firebird)
que corre entero con Docker Compose.

- Repo: `C:\Users\guille\Desktop\pp1_munitramites\munitramites`
- Rama de trabajo: `master`
- No commitear ni pushear nada mientras se esté trabajando en esta etapa.
- No tocar la rama `feature/frontend`.
- No agregar dependencias nuevas.

## Estado actual (2026-10-26)

- Base local: **138 trámites** y **682 requisitos**, sin códigos ni
  referencias internas. Es la fuente de verdad.
- El archivo de la base es **visible** en
  `datos/firebird/munitramites.fdb` (bind mount de Docker). Para Windows es
  esa ruta; dentro del contenedor sigue siendo
  `/var/lib/firebird/data/munitramites.fdb`. El volumen viejo
  `munitramites_firebird_data` queda como respaldo.
- Migración `0012_conversacionchat_mensajechat_fuentemensaje` aplicada en
  Firebird.
- Suite completa: **307 tests OK** (`docker compose exec -T web python
  manage.py test --noinput`).
- Servidor Docker arriba en `http://localhost:8000/`. La IP de LAN
  (`http://192.168.22.47:8000/`) responde desde este equipo; para que entren
  otros dispositivos falta una regla de Windows Firewall para TCP 8000
  restringida a `192.168.22.0/24` (requiere UAC).
- Cambios sin commitear: modelos/migración/vistas/plantillas/JS/CSS del
  historial del chatbot, limpieza de datos y el arreglo visual de numeración
  en `static/css/tramites.css`.

## Comandos útiles

```powershell
# Levantar / ver estado
docker compose up -d
docker compose ps
docker compose logs web --tail 40

# Django dentro del contenedor
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py makemigrations munitramites
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py test --noinput
docker compose exec -T web python manage.py test munitramites.tests.test_chatbot munitramites.tests.test_llm --noinput
```

Los tests tardan ~70 s porque corren sobre Firebird real. PowerShell muestra
el stderr de Docker como error y a veces devuelve código 1 aunque la suite
termine en `OK`; mirar la línea `Ran N tests` / `OK`.

## Datos: reglas para no romper nada

- `management/commands/cargar_datos.py` es **no-op** a propósito: no volver a
  ejecutarlo para “recargar” datos.
- **No ejecutar** scripts viejos de limpieza de `_scratch/` (la carpeta ya no
  existe): la limpieza ya está aplicada en la base.
- No borrar `datos/firebird/munitramites.fdb` ni recrear el volumen viejo
  `firebird_data` sin un backup: se pierden los 138 trámites, los requisitos y
  todo el historial de chat.
- No copiar el CSV de fuentes al Escritorio hasta que se pida.
- `usuarios.txt` contiene credenciales de prueba y una clave de Groq en texto
  plano. No copiar claves a código, docs ni commits; si se puede, rotarla y
  sacarla del repo.

## Chatbot e historial persistente

La lógica RAG vive en `munitramites/services/chatbot/` (indexar → recuperar →
generar). La vista solo orquesta y persiste.

### Modelos (`munitramites/models.py`)

- `ConversacionChat`: `usuario`, `titulo`, `creado`, `actualizado`. Título
  inicial “Nueva conversación”; se reemplaza por la primera pregunta.
- `MensajeChat`: `conversacion`, `rol` (`usuario`/`bot`), `texto`, `creado`.
- `FuenteMensaje`: `mensaje`, `tramite` (nullable), `titulo`, `orden`. Guarda
  el título tal como se mostró; si el trámite se borra, queda el título sin
  enlace.

Cada usuario ve solo sus conversaciones. `_conversacion_autorizada()` filtra
siempre por `usuario=request.user`; un id ajeno se trata como inexistente.

### Vistas y rutas (`munitramites/views/chatbot.py`)

- `GET /chatbot/` y `GET /chatbot/?c=<id>`: página completa con barra lateral.
- `POST /chatbot/`: agrega un mensaje o crea una conversación (`accion=nueva`)
  y **redirige** a `?c=<id>` para que refrescar no reenvíe el POST.
- `GET /chatbot/?q=…`: alternativa sin JavaScript; responde y redirige.
- `GET/POST /chatbot/api/`: JSON del modal. Acciones POST: mensaje libre,
  `nueva`, `seleccionar`, `limpiar`.
- `POST /chatbot/limpiar/`: vacía la conversación activa.
- `GET /buscador/api/?q=…`: barra de búsqueda; usa el mismo pipeline pero
  **no toca ninguna conversación**.

Al crear una conversación se activa en la sesión
(`request.session['chat_conversacion_id']`) y se borran las conversaciones
vacías anteriores del usuario. El historial completo queda en Firebird; a
`responder()` solo se le pasan los últimos 20 mensajes como contexto.

### Fuentes y enlaces

- El modelo **no debe devolver enlaces, URLs ni Markdown**. El prompt lo
  prohíbe (`services/chatbot/llm/prompt.py`, bloque `ENLACES`).
- Red de seguridad: `llm.limpiar_enlaces()` quita Markdown, HTML y URLs del
  texto que devuelve Groq (`services/chatbot/llm/__init__.py`).
- Las fuentes las agrega el **servidor** desde `respuesta['tramites']` y se
  guardan en `FuenteMensaje`. En la plantilla se muestran como
  `Fuente: [título](/tramites/<pk>/)`, con el título de la ficha como texto
  del enlace. Nunca se confía en un enlace generado por el modelo.

### Plantillas, JS y CSS

- `templates/chatbot.html`: página con barra lateral de conversaciones,
  sugerencias y formulario.
- `templates/parciales/chat_historial.html`: burbujas y bloque de fuentes;
  lo comparten la página y el modal.
- `templates/base.html`: modal `#modal-chat` con selector de conversaciones,
  “+ Nuevo” y “Vaciar”.
- `static/js/app.js`: carga/crea/cambia conversaciones, pinta historial y
  fuentes; el modal pide la conversación activa al abrirse.
- `static/css/app.css`: estilos de `.chat-layout`, `.chat-sidebar`,
  `.chat__fuentes`, `.chat-select` y `.chips`.

## Convenciones

- Texto de interfaz y docstrings en español rioplatense.
- Sin frameworks de JS ni build step: JavaScript puro en `static/js/app.js`.
- CSS/JS se sirven con `{% estatico %}` (`?v=<mtime>`) para evitar caché
  vieja; no hardcodear la URL del estático.
- Los tests viven en `munitramites/tests/`; usar los helpers de `base.py`.
- Firebird devuelve fechas naive y Django emite `RuntimeWarning` al guardar
  modelos con `auto_now_add`; es ruido conocido, no un fallo de tests.
