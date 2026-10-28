# munitramites

Django full stack + Firebird DB, todo corriendo con Docker.

Sin frameworks de JavaScript, sin build step y sin servicios intermedios:
**Django renderiza HTML en el servidor, habla con Firebird por ORM y maneja
login, formularios y permisos con sus propios módulos.** El único archivo JS
es `static/js/app.js` (JavaScript puro, sin dependencias): abre las pestañas
emergentes de login/registro y del asistente, maneja el historial y la barra
lateral del chat, manda las preguntas y voltea el tema claro/oscuro.
Acompañan dos scripts chicos **inline** (se cargan con la página, sin pedir
nada más): el de `base.html` que aplica el tema antes de pintar y el que deja
`window.MT` a mano de las plantillas.

Qué hace el sistema, en corto:

- **Registro simple** —usuario, correo y contraseña: el sitio no pide
  documentos ni nombres—, inicio y cierre de sesión, y **recuperación de
  contraseña por correo** (RF-15).
- Botón **ver/ocultar la contraseña** en el login, el registro y los
  formularios de clave (cambio y recuperación): aparece solo, incluso en
  forms que no lo traían en el HTML.
- **Tres roles acumulativos en el sitio**: Usuario corriente (ve trámites
  y envía consultas), Usuario administrativo (además responde consultas y
  edita trámites y temas) y Usuario administrador (además gestiona las
  cuentas del sistema), todos con un **panel propio** en `/panel/`. El
  `/admin/` de Django queda **reservado al superusuario** —ninguno de los
  tres lo ve—, y hay UNO solo: una regla que impone el código. Ver
  [Quién puede qué](#quién-puede-qué-dentro-del-panel).
- **Buscador de trámites** con filtros (texto, tema, municipio, modalidad)
  y fichas que muestran requisitos, organismo responsable, documentos
  descargables y enlaces oficiales; los temas se cargan desde el panel, no
  son opciones fijas. La búsqueda es flexible: tolera tildes, mayúsculas,
  plurales, palabras parciales y sinónimos, y ordena por relevancia. Lo que
  se escribe en «Buscar» lo responde además el asistente, en un panel arriba
  de los resultados.
- **Consultas, sugerencias y soporte** que el administrador ve, responde y
  cierra.
- **Asistente virtual** con RAG y **Groq** como modelo (API en la nube):
  vive en un modal que se abre desde cualquier página, guarda las
  conversaciones de cada cuenta y enlaza las fichas dentro del texto de la
  respuesta. Responde solo consultas sobre trámites, con redacción natural
  y flexible, cita la fuente y, si no sabe, lo dice en lugar de inventar.
  Sin clave usa las plantillas locales y no gasta la API.

Todo lo anterior está documentado acá y tiene sus tests de aceptación: ver
[Tests y trazabilidad](#tests-y-trazabilidad).

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

No necesitas instalar Python ni Firebird: todo va dentro de los contenedores.

## Arrancar

```powershell
docker compose up -d --build
```

| URL | Qué es |
|---|---|
| http://localhost:8000/ | Landing pública a pantalla completa (sin barra superior): bienvenida, ingreso (con sesión o sin cuenta) y «¿Cómo funciona?» |
| http://localhost:8000/tramites/ | Buscador de trámites |
| http://localhost:8000/perfil/ | Datos personales (pide iniciar sesión) |
| http://localhost:8000/soporte/ | Soporte (pide iniciar sesión) |
| http://localhost:8000/panel/ | **Panel de administración** (Centro de Trámites, Centro de Consultas, usuarios y temas) |
| http://localhost:8000/admin/ | Admin de Django (solo superusuario: marca Munitramites + resumen) |
| http://localhost:8000/api/tramites/ | API JSON |
| Firebird | puerto 3050 |

La primera vez tarda unos minutos (baja imágenes e instala dependencias).
El asistente **ya funciona sin configuración**: sin clave de Groq
responde con las plantillas locales del sitio. Se abre con el botón 💬 o
con los enlaces «Preguntá» de las páginas; no tiene página propia. Para que
redacte el modelo, pegá la clave en el `.env` de la raíz (ver
[Cómo redacta](#cómo-redacta-y-por-qué-no-inventa)).

### Cargar los datos de ejemplo

```powershell
docker compose exec web python manage.py cargar_datos
```

Crea 9 municipios, 7 organismos, 7 temas, 8 trámites, 32 requisitos y
3 consultas.
Es **idempotente**: se puede correr las veces que haga falta sin duplicar nada.

### Cargar los organismos reales (scraping)

Además del seed, el proyecto trae el **scraper** de sitios oficiales
(`munitramites/services/scraper/`, igual que el chatbot) con la planilla
de organismos de la provincia en
`munitramites/services/scraper/data/organismos_misiones.csv`:

```powershell
docker compose exec web python manage.py scrapear_sitios   # planilla + todos los sitios
docker compose exec web python manage.py scrapear_sitios --limite 5 --max-por-sitio 3   # corrida corta de prueba
```

| Paso | Qué hace |
|---|---|
| 1 · Planilla | importa `services/scraper/data/organismos_misiones.csv` (NOMBRE, OCUPACION, LINK_SITIO_OFICIAL) y crea los organismos que falten — idempotente, no duplica |
| 2 · Rastreo | visita cada sitio, puntúa los links (palabras fuertes/débiles, los de menú valen la mitad) y sigue solo los que huelen a trámite; si hay una «puerta» al portal (Servicios, Trámites, Turnos…), entra y busca también ahí, y de cada puerta mira sus propias puertas —las fichas están a dos o tres clicks de la home— |
| 3 · Extracción | entra a cada ficha, verifica que **sea** una ficha (no un índice ni una noticia) y saca el nombre del `<title>`/`<h1>` de la página, la descripción del primer párrafo con sustancia, los requisitos de la lista que sigue a «Requisitos» y los enlaces de turno y del sitio oficial |
| 4 · Sin repetir | no carga dos veces la misma ficha (compara la URL sin `www`, sin barra final ni fragmento) ni el mismo nombre de trámite, aunque venga de otro organismo; los requisitos repetidos se descartan |

- Todo lo que sale del scraping queda **inactivo**: se revisa, se corrige y
  se publica desde el Centro de Trámites del panel.
- Los datos se leen del contenido de la ficha, nunca del texto del link: en
  los portales el link envuelve el menú entero («Inmobiliario Trámites y
  Gestiones Información General…»).
- Un sitio caído es una fila en el resumen, no un traceback: la corrida
  sigue con el resto.
- Flags: `--csv` (otra planilla), `--limite N` (primeros N sitios),
  `--espera` (pausa entre pedidos, cortesía) y `--solo-organismos`
  (importar la planilla sin scrapear).
- Las palabras y el umbral se ajustan en
  `services/scraper/busqueda/vocabulario.py` y `services/scraper/busqueda/relevancia.py`.

## Usuarios

| Sitio | URL | Quién entra |
|---|---|---|
| Panel de administración | `/panel/` | `is_staff` (administrativo o administrador) o superusuario |
| Admin de Django | `/admin/` | Solo el superusuario (a un administrativo o administrador lo manda a `/panel/` con un aviso; al corriente Django ni lo deja pasar) |
| Consultas, soporte, perfil | `/login/` | Cualquier usuario registrado |

### Roles

El documento define tres roles **acumulativos** (cada uno puede todo lo
del anterior) y así están modelados. El rol vive en `Perfil.rol` —migración
`0005_perfil_rol`— y se mantiene sincronizado con `is_staff`, que es lo
que siguen mirando las reglas de acceso:

| Rol | En Django | Qué puede hacer |
|---|---|---|
| **Usuario corriente** | usuario normal (`is_staff` sin marcar) | registrarse, ver trámites, preguntarle al asistente, enviar consultas/sugerencias, pedir soporte, ver y editar **sus** datos |
| **Usuario administrativo** | `Perfil.rol = administrativo` (+ `is_staff`) | todo lo anterior **más** el `/panel/`: responder consultas, editar trámites y gestionar temas |
| **Usuario administrador** | `Perfil.rol = administrador` (+ `is_staff`) | todo lo anterior **más** las cuentas: crear, editar, suspender y eliminar usuarios, y cambiarles el rol |
| **Superusuario** | `is_superuser` | está **fuera** de los tres: todo lo anterior **más** el `/admin/` de Django (organismos, municipios, grupos, perfiles y borrados). **Solo puede haber UNO** |

Ninguno de los tres ve el `/admin/` de Django: el administrativo o el
administrador que lo pise recibe un aviso y termina en `/panel/`
(middleware), y al corriente Django ni lo deja pasar. El rol
administrativo, además, **no** ve la pestaña ni las URLs de Usuarios
(la vigila `models.gestiona_cuentas`).

El sitio no pide datos personales: cada cuenta es **usuario, correo y
contraseña**. El **perfil** solo guarda el rol y se identifica con un id
de cadena de caracteres (UUID); se ve también en `/admin/` → Perfiles.

**Ya creado (base de desarrollo):**

| Usuario | Contraseña | Rol |
|---|---|---|
| `guilldev08` | `Munitra2026!` | Superusuario (entra a `/admin/` y a `/panel/`) |
| `cuentas` | `Munitra2026!` | Usuario administrador (cuenta de prueba; se borra desde el panel cuando ya no haga falta) |
| `gestor` | `Munitra2026!` | Usuario administrativo (cuenta de prueba; ídem) |

### Crear cuentas

**Superusuario (uno solo).** Se da de alta desde la terminal:

```powershell
docker compose exec web python manage.py createsuperuser
```

La regla está impuesta por código (`munitramites/senales.py`): cualquier
intento de crear —o de elevar a— un segundo superusuario corta con un
`ValidationError`, salga por donde salga (admin, shell o script). Por eso
**este comando solo anda si todavía no hay ningún superusuario**; después
no hace falta: el día a día es del panel.

**Administrativos, administradores y usuarios comunes.** Se crean y se
editan desde el panel, sin terminal (esa sección es del rol administrador
o del superusuario):

1. Entrar con una cuenta administradora a `http://localhost:8000/panel/`
2. Ir a **Usuarios** → **Nuevo usuario**
3. Completar los datos y elegir el rol: «Usuario administrador» (gestiona
   las cuentas), «Usuario administrativo» (trámites, consultas y temas) o
   «Usuario corriente» (solo usa el sitio)
4. Guardar. El rol se cambia después con **Editar**; el panel **nunca**
   ofrece ser superusuario ni deja tocar la cuenta del superusuario.

También se puede crear una cuenta desde la terminal:

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model as U; U().objects.create_user('nombre', 'mail@x.com', 'clave')"
```

Y darle un rol de gestión a un usuario existente (el rol vive en el
perfil, además del `is_staff`):

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model as U; from munitramites.models import Perfil; u=U.objects.get(username='nombre'); u.is_staff=True; u.save(); Perfil.objects.get_or_create(user=u, defaults={'rol': 'administrativo'})"
```

> **Nota:** la contraseña de Firebird (`SYSDBA` / `masterkey`) es la de la base de
> datos, no tiene nada que ver con los usuarios de Django.

## El panel propio (`/panel/`)

El día a día NO pasa por `/admin/`: los roles de gestión (administrativo
y administrador) trabajan en un panel propio, con la misma marca, el
mismo CSS (`app.css`) y los mismos mensajes que el resto del sitio. Tres
piezas lo componen:

| Pieza | Archivo | Qué aporta |
|---|---|---|
| Vistas y permisos | `munitramites/views/panel.py` + `munitramites/middleware.py` | decoradores `solo_administrador` y `solo_gestor_de_cuentas` (Usuarios), dashboard con accesos, CRUD de trámites, centro de consultas, usuarios y temas; el middleware manda a `/panel/` a todo usuario de gestión que pise `/admin/` |
| Formularios | `munitramites/forms.py` | `TramitePanelForm` con los inlines `RequisitoFormSet` / `EnlaceFormSet` / `DireccionFormSet` / `ArchivoFormSet`, `UsuarioPanelForm` y `UsuarioRolForm` (con el campo `rol` de tres opciones, **sin** `is_superuser`), `RespuestaConsultaForm`, `TemaForm` |
| Plantillas y estilos | `munitramites/templates/panel/` + `static/css/app.css` (sección «PANEL DE ADMINISTRACIÓN») | `base_panel.html` con la barra de pestañas («Usuarios» solo aparece para quien gestiona cuentas) y una plantilla por sección; pestañas, filtros, filas de inlines y etiquetas de rol heredando los dos temas |

### Qué se hace desde `/panel/`

| Sección | URL | Qué permite |
|---|---|---|
| Resumen | `/panel/` | tarjetas con los números del día y atajos (la de Usuarios solo aparece para el rol administrador; los de `/admin/` solo los ve el superusuario) |
| Centro de Trámites | `/panel/tramites/` | listar todos/activos/inactivos, alta y edición con requisitos, enlaces, direcciones (varias sedes por trámite) y archivos descargables, activar / desactivar / destacar |
| Centro de Consultas | `/panel/consultas/` | ver las de todos los ciudadanos, filtrar por estado y responder (RF-10) |
| Usuarios | `/panel/usuarios/` | buscar, crear cuentas con cualquiera de los tres roles, cambiar roles, suspender y eliminar (RF-11); reservada al rol administrador |
| Temas | `/panel/temas/` | alta de temas con el conteo de trámites de cada uno (RF-07) |

Lo que el panel **no** hace, a propósito:

- **No crea ni edita superusuarios.** El formulario de alta ni siquiera
  tiene el campo; la única cuenta se hace con `manage.py createsuperuser`
  y la regla la vigila `munitramites/senales.py`.
- **No deja tocar la propia cuenta** (para eso están «Mi perfil» y
  «Cambiar mi contraseña») **ni la del superusuario**.
- **No gestiona organismos ni municipios**: esas tablas viven en
  `/admin/`, reservado al superusuario.
- **Las direcciones de atención sí se cargan desde el Centro de Trámites**:
  cada trámite puede tener varias sedes, cada una con su municipio y su
  dirección (tabla `MUNITRAMITES_DIRECCION`, «DIRECCIONES» en el diagrama).
  Si un trámite no tiene filas, la ficha pública muestra la dirección del
  organismo responsable como respaldo.
- **Los archivos descargables también**: formularios rellenables,
  instructivos y documentos se suben en el mismo formulario del trámite
  (tabla `MUNITRAMITES_ARCHIVOTRAMITE`) y aparecen en «Documentos y
  formularios» de la ficha pública, con su tipo y una descripción opcional.
  En desarrollo los sirve Django desde `/media/`; el `.gitignore` ya excluye
  esa carpeta.
- **El buscador es flexible**: `munitramites/services/busqueda.py` normaliza
  tildes y mayúsculas, recorta plurales, acepta prefijos y sinónimos del
  dominio («chofer» → licencia de conducir) y ordena por relevancia. Lo usan
  tanto el listado público como el buscador del panel.

### El admin de Django (`/admin/`)

Sigue siendo el Django con marca propia, resumen y candado — pero ahora
**solo lo ve el superusuario** (lo corta `middleware.AdminSoloSuperusuario`;
un administrativo o administrador que pise `/admin/` recibe un aviso y
termina en `/panel/`). Tres piezas lo componen:

| Pieza | Archivo | Qué aporta |
|---|---|---|
| Marca, permisos y columnas | `munitramites/admin.py` | título «Munitramites · Panel de administración», píldoras de color, filtros, buscadores, acciones masivas y el candado de roles |
| Índice con saludo y tarjetas | `munitramites/templates/admin/index.html` + `panel_resumen.html` | saludo con el nombre del que entró y tarjetas de resumen (trámites activos, consultas sin responder, sugerencias, cuentas, organismos), cada una con enlace al listado ya filtrado |
| Estilos del panel | `static/css/admin.css` | barra con el mismo degradado del sitio, tarjetas, píldoras, botones y página de ingreso. Se carga **después** de las hojas de Django (ver `templates/admin/base_site.html`), así que pisa lo que haga falta |

Detalles pensados para el día a día:

- **Atajos** en la barra lateral: consultas sin responder, trámites publicados,
  ver el sitio público y cambiar la contraseña.
- **Píldoras de color** en los listados: tema y modalidad de los trámites, tipo
  y estado de las consultas, rol de cada cuenta. Las celdas vacías se ven «—».
- **Tabla de Temas**: los temas de los trámites dejan de ser opciones fijas
  del código y se cargan desde el panel; ahí mismo aparecen en el formulario
  de alta de trámites y en los filtros del listado.
- **Acciones masivas**: *Activar / Desactivar trámites*, *Marcar como
  respondidas* (solo las que ya tienen respuesta cargada) y *Cerrar consultas*.
- **Casillas en línea** para destacar o publicar un trámite sin abrir la ficha.
- El tema oscuro de Django sigue funcionando: la hoja usa las variables de
  Django (`--body-bg`, `--border-color`, …), no colores fijos.

### Quién puede qué dentro del panel

| En Django | Corriente | Administrativo | Administrador | Superusuario |
|---|---|---|---|---|
| `/panel/`: trámites, consultas y temas | no pasa: aviso y portada | sí | sí | sí |
| `/panel/usuarios/`: cuentas y roles | no | no pasa: aviso y `/panel/` | sí | sí |
| `/admin/`: organismos, municipios, grupos, perfiles, borrados | no | no pasa: aviso y redirección a `/panel/` (middleware) | ídem | sí |
| Crear un superusuario | no (el panel ni lo ofrece) | no | no | solo puede haber **UNO**: `senales.py` corta el segundo |
| La propia fila de cuenta | no se edita ni se elimina desde el panel | ídem | ídem | se abre en modo lectura en `/admin/`: **nadie se edita ni se borra a sí mismo** |

Todo eso vive en `views/panel.py` (`solo_administrador`,
`solo_gestor_de_cuentas`, `_cuenta_protegida`), en `models.gestiona_cuentas`
(el rol vive en `Perfil.rol`), `middleware.py`, `senales.py` y `admin.py`
(`SoloSuperusuario`, `SinAutogestion`, `BaseAdmin`), y está cubierto por
`tests/test_panel.py`, `tests/test_roles.py` y `tests/test_admin.py`.

## Rutas

| URL | Vista | Acceso |
|---|---|---|
| `/` | Landing a pantalla completa (sin barra superior): hero con «Iniciar sesión» / «Continuar sin sesión» y «¿Cómo funciona?» (aparece al bajar) | público |
| `/tramites/` | Listado con filtros y paginación; arriba de todo, la chatbar del asistente | público |
| `/tramites/<id>/` | Ficha con requisitos, organismo y botones de enlaces | público |
| `/soporte/` | Formulario de soporte + pedidos del usuario | sesión |
| `/chatbot/api/` | JSON que usa el modal del asistente (historial y conversaciones) | sesión (el POST sin sesión contesta 403) |
| `/buscador/api/` | JSON del asistente para la barra «Buscar» (no guarda la charla) | público |
| `/consultas/` | Consultas del usuario (o todas, si es staff) | sesión |
| `/consultas/nueva/` | Formulario de consulta | sesión |
| `/registro/` · `/login/` | Modal de alta y de sesión, con la landing quedando detrás (también funciona como página) | público |
| `/logout/` | Cierra la sesión (RF-14) | sesión |
| `/perfil/` | Tu correo (usuario y clave no se tocan acá), más el rol y la fecha de alta | sesión |
| `/password/reset/` · `/done/` · `/<uid>/<token>/` · `/complete/` | Recuperar la contraseña olvidada (RF-15) | público |
| `/password/change/` · `/done/` | Cambio de contraseña estando adentro (página propia del sitio) | sesión |
| `/consultas/<id>/` | Detalle de la consulta y respuesta del administrador (RF-10) | sesión |
| `/panel/` | Panel propio: resumen y accesos | `is_staff` o superusuario |
| `/panel/tramites/` · `/nuevo/` · `/<id>/editar/` · `/<id>/estado/` | Centro de Trámites: CRUD + publicar/destacar | ídem |
| `/panel/consultas/` · `/panel/consultas/<id>/` | Centro de Consultas: ver todas y responder | ídem |
| `/panel/usuarios/` · `/nuevo/` · `/<id>/editar/` · `/<id>/eliminar/` | Cuentas y roles (nunca superusuarios) | **solo rol administrador** o superusuario |
| `/panel/temas/` | Alta de temas (RF-07) | `is_staff` o superusuario |
| `/admin/` | Administración de Django | **solo superusuario** (un administrativo o administrador que lo pise termina en `/panel/`) |
| `/admin/login/` | Login del admin | — |
| `/api/tramites/` | JSON con los trámites | público |

El asistente **no tiene página propia**: se usa desde el modal que se abre
en cualquier página. Las viejas rutas `/chatbot/` y `/chatbot/limpiar/` ya
no existen (el intento escrito `limpiar` sigue vaciando la charla actual).

### Piezas del layout

`base.html` lleva la barra (Inicio · Trámites · Soporte + Ingresar) y **dos
pestañas emergentes** que se usan desde cualquier página. La barra vive en el
bloque `encabezado`: la landing la vacía (`inicio.html`) para quedar como
portada a pantalla completa —con los ingresos en el propio hero y la
navegación en el pie— y el resto del sitio la muestra normal:

| Modal | Contenido | Se abre |
|---|---|---|
| `#modal-auth` | Pestañas **Ingresar** / **Crear cuenta** | clic en la barra, o solo al llegar a `/login/` y `/registro/` |
| `#modal-chat` | Chat con el asistente, hamburguesa y barra lateral con todas las conversaciones | botón 💬 flotante, la chatbar de `/tramites/`, o link con `data-abrir="modal-chat"` |

Sin JavaScript, los enlaces de login/registro caen en `/login/` y
`/registro/` (que abren el mismo modal del lado del servidor). El asistente
funciona solo con JavaScript: no hay página de chat alternativa.

Con JavaScript, el modal muestra la pregunta de una vez y un
**«Escribiendo…»** con `aria-live` mientras el servidor contesta; al
llegar la respuesta se repinta el historial que devolvió el servidor. La
hamburguesa abre la barra lateral con todas las conversaciones (título y
fecha), «+ Nuevo» crea otra y el modal recuerda conversación, scroll,
borrador y estado de la barra en `sessionStorage`; al cerrar sesión se
limpia.

La barra también trae el **interruptor de tema** (🌙 / ☀️): voltea entre el
tema claro y el oscuro, guarda la elección en `localStorage` y, si el usuario
nunca tocó nada, respeta la del sistema (`prefers-color-scheme`). `base.html`
fija `data-tema` en `<head>`, **antes de pintar**, para que no destelle el
otro tema; los dos se miden con contraste AA en `tests/test_tema.py`.

**No hay catch-all.** Una URL inexistente devuelve el 404 real de Django.

Orden en `urls.py` (importa): admin → auth → páginas → API → estáticos.
Si agregás una ruta nueva, ponla **antes** de la que empiece con `<int:...>`.

## Estructura

Todo lo de Django vive en **una sola carpeta**, `munitramites/`. Es la carpeta
que se abre una vez y están todos los archivos: configuración, vistas,
servicios, tests y plantillas. Cada cosa tiene su lugar y está documentada
en el propio archivo.

```
munitramites/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── README.md                       # ← toda la documentación (estás adentro)
├── static/
│   ├── css/app.css                 # hoja de estilos del sitio
│   ├── css/sitio.css               # rediseño (portada + trámites) para todo el sitio
│   ├── css/admin.css               # hoja de estilos del panel /admin/
│   ├── css/landing.css             # portada a pantalla completa
│   ├── css/tramites.css            # lista y ficha (tema oscuro propio)
│   ├── img/                        # andresito (portada) y banner de trámites
│   └── js/app.js                   # modales + chat: barra lateral e historial (sin frameworks)
└── munitramites/                   # ← TODO lo de Django está acá
    ├── settings.py                 #    configuración: BD, email, chatbot, idioma
    ├── urls.py                     #    rutas: acá se agregan las URL
    ├── wsgi.py / asgi.py           #    puntos de entrada del servidor
    ├── models.py                   #    las tablas de Firebird
    ├── forms.py                    #    validación en el servidor
    ├── admin.py                    #    marca, permisos y qué se ve en /admin/
    ├── senales.py                  #    regla: UN solo superusuario (pre_save)
    ├── middleware.py                #    /admin/ reservado al superusuario
    ├── context_processors.py       #    form de registro + rol de gestión del panel
    ├── apps.py                     #    identidad de la app + índice del chat
    ├── views/                      #    vistas: UN ARCHIVO POR MÓDULO
    │   ├── __init__.py             #    reexporta todo → las URL no cambian
    │   ├── pagina.py               #    landing
    │   ├── tramites.py             #    listado y ficha
    │   ├── chatbot.py              #    asistente (API del modal y de la barra; lógica en services/)
    │   ├── consultas.py            #    consultas, sugerencias y detalle
    │   ├── panel.py                #    panel /panel/: trámites, consultas, usuarios, temas
    │   ├── soporte.py              #    soporte
    │   ├── cuenta.py               #    registro y perfil
    │   └── api.py                  #    API JSON
    ├── services/                   #    lógica que no depende del request
    │   ├── README.md               #    mapa: qué hace cada archivo
    │   ├── busqueda.py             #    buscador flexible (tildes, plurales, sinónimos)
    │   ├── chatbot/                #    RAG: indexar → recuperar → generar
    │   │   ├── indexar.py          #    1. convierte trámites en fragmentos
    │   │   ├── recuperacion.py     #    2. BM25 + sinónimos + stopwords
    │   │   ├── generacion.py       #    3. plantilla local + reglas de montos
    │   │   ├── llm/                #    modelo: qué se manda y cuándo
    │   │   │   ├── prompt.py       #       la ventana de contexto (system + user)
    │   │   │   ├── groq.py         #       POST a la API de Groq
    │   │   │   └── __init__.py     #       activo / cooldown / fallback
    │   │   └── pipeline.py         #    orquestador + reglas de la charla
    │   └── scraper/                #    scraping: planilla → buscar → fichas
    │       ├── planilla.py         #    1. importa la planilla de organismos
    │       ├── busqueda/           #    2. qué link es un trámite y cuáles seguir
    │       │   ├── vocabulario.py  #       todas las palabras del dominio
    │       │   ├── relevancia.py   #       puntúa links (umbral + menú)
    │       │   └── rastreo.py      #       HTTP + candidatos + puertas
    │       ├── fichas/             #    3. de la página a la ficha
    │       │   ├── extraccion.py   #       título + requisitos + enlaces
    │       │   └── clasificacion.py#       tema, municipio y modalidad
    │       ├── servicio.py         #    orquestación del scraping
    │       └── data/
    │           └── organismos_misiones.csv   # planilla de organismos de Misiones
    ├── tests/                      #    tests de aceptación (303)
    │   ├── base.py                 #    helpers (usuarios, trámites) + TestCase
    │   ├── test_auth.py            #    ESP-01 · RF-01/02/14/15
    │   ├── test_tramites.py        #    ESP-04/06/07 · RF-07/12
    │   ├── test_scraping.py        #    scraper: relevancia + comando (sin red)
    │   ├── test_chatbot.py         #    asistente: RAG, fuentes e historial
    │   ├── test_llm.py             #    el cliente del LLM, con mocks (nunca toca el modelo)
    │   ├── test_consultas.py       #    RF-08/09/10
    │   ├── test_roles.py           #    ESP-02 · RF-03/11/13 (los tres roles)
    │   ├── test_panel.py           #    panel /panel/: matriz de aceptación
    │   ├── test_rnf.py             #    RNF-03 rendimiento · RNF-05 integridad
    │   ├── test_tema.py            #    tema claro/oscuro + contraste WCAG
    │   ├── test_estaticos.py       #    {% estatico %}: CSS/JS con ?v= para la caché
    │   └── test_admin.py           #    cara del /admin/ + candado + un solo super
    ├── migrations/                 #    migraciones generadas
    ├── management/commands/
    │   ├── cargar_datos.py         #    semilla de datos
    │   └── scrapear_sitios.py      #    cáscara fina sobre services/scraper/
    ├── templatetags/
    │   ├── estaticos.py            #    {% estatico %}: CSS/JS con ?v=<mtime>
    │   ├── hora.py                 #    filtro |hora_local
    │   └── panel_admin.py          #    {% panel_admin %}: tarjetas del panel
    └── templates/
        ├── base.html               #    layout: barra + los 2 modales
        ├── admin/
        │   ├── base_site.html      #    base de todo el panel: carga admin.css
        │   ├── index.html          #    saludo + tarjetas + atajos
        │   └── panel_resumen.html  #    las tarjetas (las arma panel_admin)
        ├── inicio.html             #    landing (también detrás de /login/ y /registro/)
        ├── soporte.html            #    soporte (solo con sesión)
        ├── parciales/
        │   ├── lista_tramites.html #    filtros + listado + paginación
        │   └── chat_historial.html #    burbujas del chat
        ├── tramites/
        │   ├── lista.html          #    buscador + filtros
        │   └── detalle.html        #    ficha con requisitos
        ├── consultas/
        │   ├── lista.html          #    mis consultas
        │   ├── nueva.html          #    formulario
        │   └── detalle.html        #    consulta + respuesta (RF-10)
        ├── panel/
        │   ├── base_panel.html     #    base del panel: título + pestañas
        │   ├── dashboard.html      #    resumen y accesos (/panel/)
        │   ├── tramites_lista.html #    Centro de Trámites
        │   ├── tramite_form.html   #    alta/edición + requisitos, enlaces y direcciones
        │   ├── consultas_lista.html#    Centro de Consultas
        │   ├── consulta_detalle.html #  ver y responder (RF-10)
        │   ├── usuarios_lista.html #    cuentas con roles (RF-11)
        │   ├── usuario_form.html   #    alta/edición de cuentas
        │   └── temas.html          #    alta de temas (RF-07)
        ├── cuenta/
        │   └── perfil.html         #    correo editable + rol y alta de la cuenta
        └── registration/
            ├── login.html          #    deja el modal de login abierto
            ├── password_reset_form.html     # RF-15: pide el correo
            ├── password_reset_done.html     # RF-15: avisó que se envió
            ├── password_reset_confirm.html  # RF-15: clave nueva
            ├── password_reset_complete.html # RF-15: listo
            └── password_change_done.html    # aviso de cambio de clave
```

### Criterios de diseño (por qué está así)

| Decisión | Motivo |
|---|---|
| **Un solo directorio** `munitramites/` | configuración y app juntas: no hay que adivinar dónde vive cada cosa |
| `views/` por módulo, `services/` aparte | la vista solo coordina request → servicio → plantilla; la lógica reutilizable se prueba sin HTTP |
| `__init__.py` que re-exporta | las URL siguieron igual (`views.inicio`), así que mover código no rompe nada |
| `apps.py` con `name = 'munitramites'` | conserva el prefijo de tabla en Firebird (`munitramites_tramite`, …) y las migraciones existentes |
| `TEMPLATES['DIRS']` apuntando a `templates/` | las plantillas del sitio tienen prioridad sobre las que traen `django.contrib.admin` y `django.contrib.auth` |
| `tests/` con helpers en `base.py` | los criterios de aceptación del documento se prueban de punta a punta |

### ¿Dónde toco para...?

| Quiero... | Archivo | Después |
|---|---|---|
| Agregar una ruta / vista | `views/<modulo>.py` + `__init__.py` + `urls.py` | — |
| Crear una tabla nueva | `models.py` | `makemigrations` + `migrate` |
| Ver una tabla en `/admin/` | `admin.py` | — |
| Cambiar la cara del panel (tarjetas, colores, saludo) | `templates/admin/` + `static/css/admin.css` | — |
| Ajustar quién puede qué en el panel | `admin.py` → `BaseAdmin` / `SoloSuperusuario` / `SinAutogestion` | `test_admin` |
| Cambiar requisitos o botones de una ficha | `/panel/tramites/` → **Editar** (requisitos numerados y enlaces con nombre y URL) | — |
| Cambiar el rol de una cuenta o el correo | `/admin/` → Usuarios → fila → **Perfil** (rol de solo lectura) | — |
| Crear una página nueva | `templates/` + `views/<modulo>.py` + `urls.py` | — |
| Agregar un campo a un formulario | `forms.py` | — |
| Mejorar lo que sabe el asistente | `services/chatbot/` (ver sección siguiente) | — |
| Agregar sinónimos al asistente | `services/chatbot/recuperacion.py` → `SINONIMOS` | — |
| Cambiar el diseño | `static/css/app.css` + `static/css/sitio.css` (rediseño: tokens y componentes de todo el sitio) + `templates/base.html` (lista, ficha y chat: `static/css/tramites.css`; panel: `static/css/admin.css`) | — |
| Agregar un filtro de template | `templatetags/hora.py` | `{% load hora %}` |
| Cambiar un CSS o un JS | `static/` | `{% estatico %}` (le agrega `?v=<mtime>` para la caché) |
| Cargar datos de ejemplo | `management/commands/cargar_datos.py` | `cargar_datos` |
| Cargar organismos y trámites reales | `services/scraper/` (con su `data/organismos_misiones.csv`) | `scrapear_sitios` |
| Cambiar el modelo del asistente | `.env` → `GROQ_MODELO` (+ `services/chatbot/llm/`) | `docker compose up -d web` |
| Correr los tests | `tests/` | `manage.py test --noinput` |
| Cambiar la base de datos | `settings.py` → `DATABASES` | — |
| Cambiar idioma / zona horaria | `settings.py` → `LANGUAGE_CODE` / `TIME_ZONE` | — |
| Cambiar login / redirecciones | `settings.py` → bloque `LOGIN_*` | — |
| Mover el admin de ruta | `urls.py` → línea `path('admin/', ...)` | — |
| Agregar una dependencia | `requirements.txt` | `docker compose up -d --build` |

### El ciclo de trabajo

```
1. models.py            crear la tabla
2. admin.py             registrarla para verla en /admin/
3. forms.py             validar los datos
4. views/<modulo>.py    consultar y guardar (llamando a services/ si hay lógica)
5. templates/           mostrar el resultado
6. urls.py              exponer la ruta
7. tests/               dejar el criterio de aceptación escrito y en verde
```

## Comandos útiles

```powershell
docker compose ps                          # estado de los contenedores
docker compose logs -f web                 # ver logs de Django en vivo
docker compose down                        # parar (CONSERVA la base)
docker compose down -v                     # parar y BORRAR la base
docker compose build --no-cache            # reconstruir desde cero

docker compose exec web python manage.py check                  # revisar el código
docker compose exec web python manage.py makemigrations         # generar migración
docker compose exec web python manage.py migrate                # aplicar
docker compose exec web python manage.py cargar_datos           # sembrar datos
docker compose exec web python manage.py scrapear_sitios        # importar la planilla y scrapear los sitios oficiales
docker compose exec web python manage.py shell                  # consola Django
docker compose exec web python manage.py test --noinput         # correr los 303 tests
docker compose exec web python manage.py ver_contexto "¿qué necesito para renovar el DNI?"  # ver el contexto que se manda a Groq

docker compose logs -f web                                     # ver los pedidos a Groq
```

### Ejecutar código desde el host

PowerShell no soporta `<`, así que se usa pipe:

```powershell
# Opción A: un archivo
Get-Content script.py -Raw | docker compose exec -T web python manage.py shell

# Opción B: una línea
"print(1+1)" | docker compose exec -T web python manage.py shell
```

## Git

| | |
|---|---|
| Repositorio | <https://github.com/guilldev08/pp1_munitramites> |
| Raíz del repo | `C:\Users\guille\Desktop\pp1_munitramites\munitramites` (la carpeta que tiene `manage.py`) |
| Rama | `master`, siempre igual a `origin/master` |

**Solo existe un `.git`**, el de esa raíz. Abrir el proyecto desde la carpeta
de arriba (`pp1_munitramites\`) hace que algunas herramientas muestren
«cambios» que no existen: ahí no hay repositorio. Si aparece un `.git` de más
no se inicializa otro, se elimina ese.

Qué deja afuera el `.gitignore`: `__pycache__/`, entornos virtuales, `*.fdb`
(las bases de Firebird), `.env` y claves, logs, `.vscode/` y cachés de
linters.

Flujo habitual:

```powershell
git status          # qué cambió
git add -A
git commit -m "qué se hizo"
git push origin master
```

## Tests y trazabilidad

```powershell
docker compose exec web python manage.py test --noinput          # todo
docker compose exec web python manage.py test munitramites.tests.test_auth --noinput   # un archivo
docker compose exec web python manage.py test munitramites.tests.test_auth.RecuperarClaveTests --noinput  # una clase
```

El `--noinput` evita la pregunta interactiva cuando queda una base de test
puesta. Django crea y destruye sola la base `munitramites_test.fdb` (el nombre
está fijado en `settings.DATABASES['default']['TEST']`; sin eso, `django-firebird`
arma un nombre con la ruta completa que Firebird no puede crear).

`munitramites/tests/base.py` trae los helpers (`ciudadano()`, `administrador()`,
`tramite()`, …) y un `TestCase` propio que limpia el índice del asistente entre
tests. **Si agregás una funcionalidad nueva, dejá su criterio de aceptación
escrito acá**: es lo que hace verificable el documento.

**Códigos sin fila en la tabla**: ESP-03, RF-04 y RF-06 no tienen requisito
propio en este sistema. **RF-05** (*Gestionar organismos*) sí existe y está en
el código (`admin.py`, sección *Organismos*); lo cubren
`test_admin.SuperusuarioTests` (alta con el área de acción, desde `/admin/`)
y `test_tramites` (la ficha los muestra), por eso se cita en el archivo y no
en esta tabla.

| Documento | Dónde está en el código | Test |
|---|---|---|
| **ESP-01** Autenticación | `forms.py`, `views/cuenta.py`, `templates/registration/` | `test_auth` |
| **ESP-02** Roles | `views/panel.py` (decoradores `solo_administrador` y `solo_gestor_de_cuentas`), `models.Perfil.rol` + `models.gestiona_cuentas`, `middleware.py` | `test_roles` · `test_panel` · `test_admin` |
| **ESP-04** Administración | `/panel/` (`views/panel.py`) + `/admin/` (`admin.py`) | `test_panel` · `test_roles` · `test_tramites` · `test_admin` |
| **ESP-05** Consultas | `views/consultas.py`, `models.Consulta` | `test_consultas` |
| **ESP-06** Base de datos | Firebird + `models.py` + `migrations/` | todos (corren sobre Firebird) |
| **ESP-07** Interfaz | `templates/`, `static/css/app.css`, sin JS obligatorio | `test_tramites` · `test_chatbot` · `test_panel.DisenoTests` · `test_tema` · `test_tramites.ApiTests` |
| **RF-01** Registro de usuario | `views/cuenta.py::registro` (usuario, correo y clave: sin datos personales) | `test_auth.RegistroTests` · `test_auth.PerfilTests` (editar su correo) |
| **RF-02** Inicio de sesión | modal de `base.html` + `LoginView` | `test_auth.SesionTests` |
| **RF-03** Gestión de roles | `models.Perfil.rol` (corriente / administrativo / administrador) con `is_staff` sincronizado + `forms.UsuarioRolForm` | `test_roles` · `test_panel.UsuariosTests` · `test_admin` |
| **RF-07** Administrar trámites | `/panel/tramites/` (con Requisitos, Enlaces, Direcciones y Archivos) + búsqueda flexible en `services/busqueda.py` | `test_panel.CentroDeTramitesTests` · `test_tramites` · `test_roles` |
| **RF-08** Enviar consultas | `views/consultas.py::consulta_nueva` | `test_consultas` |
| **RF-09** Enviar sugerencias | mismo formulario, `tipo = sugerencia` | `test_consultas` |
| **RF-10** Gestionar consultas | `/panel/consultas/<id>/` + `/consultas/<id>/` | `test_panel.CentroDeConsultasTests` · `test_consultas.GestionDelAdminTests` |
| **RF-11** Gestionar usuarios | `/panel/usuarios/` (tres roles, sin tocar superusuarios; sección del rol administrador) | `test_panel.UsuariosTests` · `test_roles.AdministradorTests` · `test_roles.AdministrativoTests` |
| **RF-12** Almacenamiento de datos | Firebird vía ORM | todos |
| **RF-13** Control de acceso | `LoginRequired` + `solo_administrador` + `solo_gestor_de_cuentas` + `middleware.AdminSoloSuperusuario` + `senales.py` | `test_roles.AnonimoTests` · `test_roles.AdministrativoTests` · `test_panel.AccesoTests` · `test_auth.SesionTests` · `test_admin.EditorRedirigidoTests` · `test_admin.UnSoloSuperusuarioTests` |
| **RF-14** Cerrar sesión | `/logout/` | `test_auth.SesionTests` |
| **RF-15** Recuperar/restablecer contraseña | `urls.py` + `templates/registration/password_reset_*` | `test_auth.RecuperarClaveTests` · `test_auth.PerfilTests` (cambio estando adentro) |
| **IA — precisión contextual** | `services/chatbot/recuperacion.py` (BM25 + umbral) | `test_chatbot.PipelineTests` |
| **IA - alucinaciones** | `services/chatbot/llm/prompt.py` (el prompt prohíbe inventar montos y citas) · `generacion.py` (sin modelo: el corte de montos contesta «no dispongo» por un precio que no está indexado) · `pipeline.py` (`_SIN_INFO`) | `test_chatbot` · `test_chatbot.AlucinacionesTests` · `test_llm` |
| **IA — cita de fuentes** | `Fragmento.tramite_id` → enlace a la ficha | `test_chatbot` |
| **IA — historial y privacidad** | `ConversacionChat`/`MensajeChat`/`FuenteMensaje` en Firebird, filtrados por usuario; cada cuenta ve solo lo suyo | `test_chatbot.HistorialPersistenteTests` |
| **IA — barra de búsqueda** | `views/chatbot.py::buscador_api` (mismo `responder()`, sin tocar el historial) · panel en `lista_tramites.html` + `app.js` | `test_chatbot.BuscadorTests` |
| **RNF-01** Seguridad | sesión y contraseña de Django (`login_required`, CSRF, hasher), correos únicos, «cada uno ve lo suyo» | `test_roles` · `test_admin` · `test_consultas` |
| **RNF-02** Usabilidad | plantillas con `label` y `help_text`, filtros en `/tramites/`, formularios con mensajes de error en español | `test_consultas` · `test_tramites` |
| **RNF-03** Rendimiento | `select_related` + `prefetch_related`, 6 por página (`views/tramites.py::POR_PAGINA`) e índice BM25 en memoria | `test_rnf.RendimientoTests` (sin N+1 y caché del índice) · `test_tramites.ListadoTests.test_paga_de_a_seis_por_pagina` |
| **RNF-04** Disponibilidad | `restart: unless-stopped`, healthcheck de Firebird y espera activa del `web` en `docker-compose.yml` | — |
| **RNF-05** Integridad | `unique` (Municipio/Organismo), `unique_together` (Requisitos), `PROTECT`/`CASCADE` en las claves foráneas | `test_rnf.IntegridadTests` · `test_auth` |
| **RNF-06** Mantenibilidad | `views/` por módulo, `services/`, docstrings y este README | — |
| **RNF-07** Compatibilidad | el entorno definido del proyecto (Docker); login y registro andan sin JavaScript y el asistente se resuelve en el modal | `test_chatbot` · `test_tramites` |
| **RNF-08** Escalabilidad | capas independientes (vista ↔ servicio ↔ plantilla) y `INSTALLED_APPS` | — |
| **RNF-09** Despliegue (Docker) | `Dockerfile` + `docker-compose.yml` | — |
| **RNF-10** Respaldo de BD | sección «Respaldo de la base» más abajo | — |
| **RNF-11** Accesibilidad | `label`, `aria-label`, `aria-modal`, foco visible, cierre con `Esc` y tema claro/oscuro con contraste AA | `test_chatbot` · `test_tema` |

## Asistente virtual (RAG)

El chatbot **no adivina**: arma un índice con los trámites, busca los
fragmentos que responden la pregunta y responde citando de dónde salió.
Todo vive en `services/chatbot/`, en cuatro piezas.

| Etapa | Archivo | Qué hace |
|---|---|---|
| 1 · Indexar | `indexar.py` | convierte cada trámite activo en fragmentos (ficha + un fragmento por requisito) con su fuente. Se guarda en memoria y **se invalida solo** cuando cambian trámites, requisitos, municipios u organismos (las señales están en `indexar.py` y se conectan desde `apps.py`) |
| 2 · Recuperar | `recuperacion.py` | normaliza (minúsculas, sin acentos, sin palabras de relleno), expande con `SINONIMOS` (dni → documento, licencia → conducir, …) y puntúa con BM25. Todo lo que queda bajo `CHATBOT_UMBRAL` se descarta |
| 3 · Generar | `generacion.py` | redacta con los fragmentos recuperados: con clave de Groq (**`GROQ_MODELO`**, vía `llm/`) la frase la arma el LLM citando el contexto; sin fichas puede explicar el portal o redirigir; sin clave o si falla cae a `PlantillaLocal` (plantillas con variantes, sin costo). Una pregunta por monto que no está indexada se corta antes de redactar cuando no hay modelo |
| LLM | `llm/` | cliente de Groq (API compatible con OpenAI): `prompt.py` arma la ventana de contexto, `groq.py` hace el POST y `__init__.py` decide cuándo llamar (cooldown tras un fallo). Redacta con o sin contexto, **siempre dentro de los trámites**; los datos salen siempre del contexto (nunca los inventa) |
| Orquestador | `pipeline.py` | saludos y ayuda sin buscar, devuelve `{'texto', 'tramites', 'fragmentos'}`. Con contexto → el modelo redacta; sin contexto → el modelo explica el portal o redirige si el tema es ajeno; sin modelo o en la barra pública, el «no dispongo» citando la consulta. Nunca inventa nada |

**Se le puede preguntar desde tres lugares**: el modal 💬 (desde cualquier
página), la **chatbar de `/tramites/`** (arriba de todo en el listado: abre
el mismo modal y manda la pregunta) y la **barra de búsqueda del sitio**:
lo que se escriba en «Buscar» filtra la lista y, arriba de los resultados,
un panel con el mismo pipeline redacta la respuesta
(`parciales/lista_tramites.html` + `app.js`). Ese panel sale por
`/buscador/api/?q=…`, que llama al mismo `responder()` que el chat pero
**sin tocar el historial**: lo que se busca no queda en la charla
(privacidad, verificado en vivo). Sin sesión iniciada ese panel responde
con plantillas —el modelo solo redacta para usuarios logueados—, así que
una visita anónima no gasta la API de Groq. Sin JavaScript el panel muestra
el enlace que abre el modal con la misma pregunta (`data-chat-pregunta`).
Tests: `test_chatbot.BuscadorTests`.

### Historial por usuario

Cada cuenta tiene sus propias conversaciones, guardadas en Firebird
(`ConversacionChat`, `MensajeChat` y `FuenteMensaje`). El modal trae una
hamburguesa que abre la barra lateral con **todas** las conversaciones
(título y fecha), «+ Nuevo» para empezar otra y la conversación activa
resaltada. No hay botón «Vaciar»: la orden escrita `limpiar` sigue vaciando
la charla actual.

El modelo no arma enlaces: `llm.limpiar_enlaces()` descarta Markdown, HTML y
URLs que devuelva, y el servidor enlaza **dentro del texto** la primera
aparición del título de cada ficha citada (`_segmentos_con_enlaces()` en
`views/chatbot.py`); no se agrega una sección «Fuentes» al pie.
Tests: `test_chatbot.HistorialPersistenteTests` y
`test_llm.LimpiarEnlacesTests`.

### Cómo redacta (y por qué no inventa)

**El modelo lo corre Groq** (API en la nube, compatible con OpenAI):
`llm/groq.py` manda la pregunta con los fragmentos del índice a
`https://api.groq.com/openai/v1/chat/completions` y la respuesta vuelve
en segundos, sin bajar ni mantener ningún modelo en la PC. La clave va
en el `.env` de la raíz —nunca al repo, `.env` está en `.gitignore`—:

```powershell
# .env (al lado de docker-compose.yml)
GROQ_API_KEY=gsk_...
```

y se aplica recreando el servicio web:

```powershell
docker compose up -d web
```

El modelo por defecto es `openai/gpt-oss-120b` (`GROQ_MODELO` en el
`.env` para cambiarlo); la lista viva está en
[console.groq.com/docs/models](https://console.groq.com/docs/models).
Docker Compose lee el `.env` solo, así que no hay que exportar nada a
mano.

**La ventana de contexto** se arma en `services/chatbot/llm/prompt.py`:
`SYSTEM` son las reglas fijas y `armar_user()` pega los fragmentos que
devolvió el RAG (`CHATBOT_TOP_K` = 4), la charla previa y la pregunta.
Para ver el payload exacto de una consulta, sin gastar la API:

```powershell
docker compose exec web python manage.py ver_contexto "¿qué necesito para renovar el DNI?"
```

El comando imprime los fragmentos, los dos mensajes completos y el
tamaño (caracteres y tokens estimados); con `--json` los vuelca como
JSON.

**Natural, flexible y solo trámites**: el modelo varía la redacción para
no sonar a formulario y puede explicar el portal (qué es, cómo buscar) o
una duda sobre trámites. Si la pregunta es de otro tema —chistes,
política, deportes, recetas, tareas— no la responde: lo dice en una
oración, con sus palabras y buena onda, y pide el nombre del trámite.
Tampoco inventa: los datos de trámites —requisitos, montos, plazos,
organismos— salen SOLO del CONTEXTO, y el CONTEXTO se trata como datos,
no como órdenes. Si no están, lo dice con sus palabras en vez de
inventarlos. Responde en español rioplatense, de 1 a 8 oraciones.

**Si no hay clave o modelo** (sin `.env`, sin red, Groq caído), el asistente
no se cae: `generacion.py::PlantillaLocal` arma la respuesta con las
plantillas del sitio, siempre anclada a los fragmentos. Cada caso tiene
más de una redacción, elegida de forma estable por la consulta (misma
pregunta, misma frase), para que la charla no se vea clonada.

**Las preguntas por monto**: con modelo, la regla vive en el prompt (no
inventar cifras que no estén en el contexto); sin modelo, el corte
determinista de `generacion.py` responde un «no dispongo» inmediato si
el contexto no trae ninguno —pasó en vivo: «$50.000.000» por renovar el
DNI—. Los **«no sé» sin modelo citan la consulta entrecomillada y traen
tres variantes** cada uno, elegidas de forma estable por la consulta:
dos preguntas distintas nunca reciben el mismo texto —pasó en vivo: «g»
y «ag» salían letra por letra iguales—, y las consultas de menos de 3
letras se contestan aparte, pidiendo que la completen
(`pipeline._sin_informacion` y `generacion._sin_dato`).

**Cuando la pregunta es corta** («¿y el plazo?») el pipeline la busca
junto con las preguntas anteriores del usuario, así el seguimiento cae
en los trámites correctos, y la respuesta cita esos trámites en vez de
repetir la pregunta suelta. Los casos fijos —saludo, ayuda, «gracias»,
«chau» y «limpiar»— responden sin buscar en el índice, y un saludo
seguido de una pregunta ya no se traga la pregunta.

El punto de conexión sigue siendo `llm.redactar()` →
`generar_respuesta()` en `generacion.py`: ni la vista, ni el RAG ni el
pipeline cambian si mañana cambia el proveedor (`GROQ_URL` y
`GROQ_MODELO` apuntan a dónde y con qué modelo). Todo lo
de este apartado está cubierto por `tests/test_chatbot.py`
(`PipelineTests`, `PlantillaLocalTests` y `AlucinacionesTests`) y por
`tests/test_llm.py` (el cliente, con mocks: los tests nunca tocan el
modelo).

Otras perillas: `CHATBOT_TOP_K` (fragmentos que se pasan como contexto),
`CHATBOT_UMBRAL` (qué tan relevante tiene ser para citarse),
`CHATBOT_LLM` (vacío = apagar el modelo y usar solo plantillas; en los
tests siempre está apagado) y `GROQ_MODELO` / `GROQ_TIMEOUT` (modelo y
segundos de espera del proveedor).

Para agregar vocabulario del dominio, sumá entradas a `SINONIMOS` en
`recuperacion.py`; para indexar otra cosa (por ejemplo las FAQ), ampliá
`indexar.py`.

## Respaldo de la base (RNF-10)

La base vive en el volumen `firebird_data`. Opciones:

```powershell
# A) Dump lógico con gbak (portable, se puede restaurar en otra versión)
docker compose exec firebird gbak -b -user SYSDBA -password masterkey \
  /var/lib/firebird/data/munitramites.fdb /tmp/munitramites.fbk
docker compose cp firebird:/tmp/munitramites.fbk .\munitramites.fbk

# B) Copia del archivo completo (parado, o con el sitio en uso a riesgo propio)
docker compose stop firebird
docker compose cp firebird:/var/lib/firebird/data/munitramites.fdb .\munitramites.fdb
docker compose start firebird
```

Restaurar en otra instancia:

```powershell
docker compose cp .\munitramites.fbk firebird:/tmp/munitramites.fbk
docker compose exec firebird gbak -c -user SYSDBA -password masterkey \
  /tmp/munitramites.fbk /var/lib/firebird/data/munitramites_restaurada.fdb
```

> **Ojo:** `docker compose down -v` **borra el volumen** y con él la base.
> Hacé el dump antes.

## Accesibilidad (RNF-11)

- Todos los campos de formulario tienen `<label for>`; los campos del chat, que
  no tienen texto visible, llevan `aria-label`.
- Los modales son `role="dialog"` con `aria-modal`, `aria-labelledby` y botón de
  cierre con nombre accesible; se pueden cerrar con `Esc`.
- Login y registro funcionan **sin JavaScript**: los enlaces caen en
  `/login/` y `/registro/`, que abren el mismo modal del lado del servidor.
  El asistente vive en el modal y necesita JavaScript; no hay página de chat
  alternativa.
- El contraste, el orden de tabulación y los tamaños de texto están en
  `static/css/app.css` + `static/css/sitio.css` (incluye
  `prefers-reduced-motion`). Los pares de color de los **dos temas** (claro y
  oscuro) se calculan contra WCAG AA (4,5:1) en `tests/test_tema.py`: si alguien
  mueve un gris, se entera el test.

## Acceder a la base de datos

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey localhost:/var/lib/firebird/data/munitramites.fdb
```

Luego escribí SQL y cerrá con `quit;`.

### Tablas

| Tabla | Registros | Origen |
|---|---|---|
| `MUNICIPIO` | 9 | seed |
| `ORGANISMO` | 7 | seed (incluye `ocupacion` / área de acción) |
| `TRAMITE` | 8 | seed |
| `REQUISITO` | 32 | seed |
| `ENLACE` | 5 | botones con nombre y URL que carga el seed (el panel los agrega, edita y borra); los campos viejos `enlace_turnos` / `enlace_oficial` quedan solo como respaldo |
| `DIRECCION` | 0+ | sedes de atención que se cargan desde el panel: lugar, municipio y dirección; un trámite puede tener varias |
| `CONSULTA` | 3+ | seed + formularios (incluye el prefijo `Soporte: `) |
| `CONVERSACION_CHAT` | 0+ | conversaciones del asistente, una por charla y usuario |
| `MENSAJE_CHAT` | 0+ | mensajes de cada conversación |
| `FUENTE_MENSAJE` | 0+ | fichas citadas por cada respuesta |
| `PERFIL` | 1+ | se crea con el registro (guarda el rol; su id es un UUID) |
| `AUTH_USER` | 2 | Django (usuarios) |
| + 9 tablas de Django | — | auth, sessions, admin, contenttypes |

## Stack

| Componente | Versión | Imagen |
|---|---|---|
| Python | 3.11 | `python:3.11-slim` |
| Django | 5.2 LTS | (pip) |
| Backend Firebird | `django-firebird` 5.0.4 | (pip) |
| Driver | `firebird-driver` 2.0.3 | (pip) |
| Firebird Server | 4.0.7 | `firebirdsql/firebird:4.0.7` |
| Asistente | — | Groq API (`openai/gpt-oss-120b` por defecto), sin modelo local |

Credenciales de la base (solo desarrollo): `SYSDBA` / `masterkey`

> **Asistente**: la generación con Groq necesita `GROQ_API_KEY` en el
> `.env` y conexión a internet; sin ninguna de las dos, el sitio entero
> funciona igual con las plantillas locales (no hay modelo en la PC ni
> volumen que mantener).

## Notas

- **Idioma `es-ar`, zona horaria `America/Argentina/Buenos_Aires`.**
- Firebird guarda `TIMESTAMP` sin zona horaria. Con `USE_TZ=True` Django guarda
  en UTC, así que el filtro `|hora_local` (en `templatetags/hora.py`) convierte
  a hora local antes de mostrar. Usalo siempre: `{{ fecha|hora_local|date:"d/m/Y H:i" }}`.
- `settings.py` apunta a `/var/lib/firebird/data/...`, que es la ruta **vista
  desde el servidor Firebird**, no desde tu PC.
- El volumen `firebird_data` guarda la base. Para llevarla a otra PC, hacé el
  dump de [Respaldo de la base (RNF-10)](#respaldo-de-la-base-rnf-10) antes de
  `docker compose down -v`.
- **Los correos salen por la consola**: `EMAIL_BACKEND` está en la consola, así
  que el enlace de recuperación de contraseña (RF-15) se ve con
  `docker compose logs web`. En producción hay que poner un backend SMTP.
- Los contenedores tienen `restart: unless-stopped`: se levantan solos si Docker
  Desktop se reinicia.

### Pendiente para producción

`manage.py check --deploy` reporta **6** avisos (verificados con el comando),
todos esperados en desarrollo:

| Aviso | Cómo resolverlo |
|---|---|
| `W018` `DEBUG = True` | `DEBUG = False` |
| `W009` `SECRET_KEY` | generar una clave real y sacarla del repositorio |
| `W004` HSTS | `SECURE_HSTS_SECONDS` (recién cuando el sitio sea solo HTTPS) |
| `W008` SSL redirect | `SECURE_SSL_REDIRECT = True`, o el proxy que redirija a HTTPS |
| `W012` cookies de sesión | `SESSION_COOKIE_SECURE = True` |
| `W016` cookies CSRF | `CSRF_COOKIE_SECURE = True` |

Aparte (lo toca el deploy, no `--deploy`): `ALLOWED_HOSTS = ['*']` es de
desarrollo; en producción se listan los dominios reales.

Además: `runserver` es el servidor de desarrollo. En producción usar gunicorn
(ya está en `requirements.txt`) o un servidor WSGI equivalente.
