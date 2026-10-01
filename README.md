# munitramites

Django full stack + Firebird DB, todo corriendo con Docker.

Sin frameworks de JavaScript, sin build step y sin servicios intermedios:
**Django renderiza HTML en el servidor, habla con Firebird por ORM y maneja
login, formularios y permisos con sus propios módulos.** El único archivo JS
es `static/js/app.js` (JavaScript puro, sin dependencias): abre las pestañas
emergentes de login/registro y de chat, manda las preguntas al asistente y
voltea el tema claro/oscuro. Acompañan tres scripts chicos **inline** (se
cargan con la página, sin pedir nada más): el de `base.html` que aplica el
tema antes de pintar, el que deja `window.MT` a mano de las plantillas y el
de `chatbot.html` que mantiene el historial abajo del todo.

Qué hace el sistema, en corto:

- **Registro con DNI**, inicio y cierre de sesión, y **recuperación de
  contraseña por correo** (RF-15).
- **Dos roles en el sitio**: Usuario (ciudadano) y Administrador (panel
  `/admin/`). Dentro del panel, además, la escalera de dos peldaños que
  describe [Quién puede qué](#quién-puede-qué-dentro-del-panel): el *editor*
  no toca usuarios ni borra, y solo el *superusuario* administra cuentas.
- **Buscador de trámites** con filtros y fichas que muestran requisitos,
  organismo responsable y enlaces oficiales. Lo que se escribe en «Buscar»
  lo responde además el asistente, en un panel arriba de los resultados.
- **Consultas, sugerencias y soporte** que el administrador ve, responde y
  cierra.
- **Asistente virtual** con RAG: busca en los trámites reales, cita la fuente
  y, si no sabe, lo dice en lugar de inventar.

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
| http://localhost:8000/ | Sitio público (portada + buscador de trámites) |
| http://localhost:8000/tramites/ | Buscador de trámites |
| http://localhost:8000/chatbot/ | Asistente virtual (página completa) |
| http://localhost:8000/perfil/ | Datos personales (pide iniciar sesión) |
| http://localhost:8000/soporte/ | Soporte (pide iniciar sesión) |
| http://localhost:8000/admin/ | **Panel de administración** (marca Munitramites + resumen) |
| http://localhost:8000/api/tramites/ | API JSON |
| Firebird | puerto 3050 |

La primera vez tarda unos minutos (baja imágenes e instala dependencias).

**El modelo del asistente es opcional**: el servicio `ollama` está detrás
del perfil `llm`, así que `docker compose up -d` **no lo descarga** y el
sitio arranca igual. Sin modelo el asistente responde con la plantilla
local; para que redacte con Qwen hace falta internet (la primera vez baja
~4,5 GB: imagen + modelo) y un solo comando:

```powershell
docker compose --profile llm up -d --build   # arma la imagen con Qwen adentro
docker compose exec ollama ollama list       # qwen2.5:1.5b aparece ahí
```

### Cargar los datos de ejemplo

```powershell
docker compose exec web python manage.py cargar_datos
```

Crea 9 municipios, 7 organismos, 8 trámites, 32 requisitos y 3 consultas.
Es **idempotente**: se puede correr las veces que haga falta sin duplicar nada.

## Usuarios

| Sitio | URL | Quién entra |
|---|---|---|
| Administración | `/admin/` | Solo usuarios con `is_staff` |
| Consultas, soporte, perfil | `/login/` | Cualquier usuario registrado |

### Roles

El documento define dos roles y así están modelados:

| Rol | En Django | Qué puede hacer |
|---|---|---|
| **Usuario** (ciudadano) | usuario normal | registrarse, ver trámites, preguntarle al asistente, enviar consultas/sugerencias, pedir soporte, ver y editar **sus** datos |
| **Administrador** | `is_staff` (+ `is_superuser`) | todo lo anterior **más** el panel `/admin/`: trámites, requisitos, enlaces, organismos, municipios, consultas, sugerencias y usuarios |

Cada registro lleva un **perfil** con el DNI (dato personal que pide el
documento), visible también en `/admin/` → Usuarios.

**Ya creado:**

| Usuario | Contraseña | Rol |
|---|---|---|
| `guilldev08` | `Munitra2026!` | Superusuario (entra a `/admin/`) |

Crear otro superusuario:

```powershell
docker compose exec web python manage.py createsuperuser
```

Crear un usuario normal desde la terminal:

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model as U; U().objects.create_user('nombre', 'mail@x.com', 'clave')"
```

Dar permisos de staff a un usuario existente:

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model as U; u=U.objects.get(username='nombre'); u.is_staff=True; u.save()"
```

> **Nota:** la contraseña de Firebird (`SYSDBA` / `masterkey`) es la de la base de
> datos, no tiene nada que ver con los usuarios de Django.

## El panel (`/admin/`)

No es el Django pelado: tiene la marca del sitio, un resumen del día y un
candado de permisos. Tres piezas lo componen:

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
- **Acciones masivas**: *Activar / Desactivar trámites*, *Marcar como
  respondidas* (solo las que ya tienen respuesta cargada) y *Cerrar consultas*.
- **Casillas en línea** para destacar o publicar un trámite sin abrir la ficha.
- El tema oscuro de Django sigue funcionando: la hoja usa las variables de
  Django (`--body-bg`, `--border-color`, …), no colores fijos.

### Quién puede qué dentro del panel

`is_staff` por sí solo no alcanza: hay una escalera de dos peldaños.

| En `/admin/` | Editor (`is_staff`, sin superusuario) | Superusuario |
|---|---|---|
| Trámites, Requisitos, Enlaces, Municipios, Organismos, Consultas | alta y edición | **+ borrado** |
| Usuarios, Grupos (los roles) y Perfiles (DNI) | no aparece en el índice y responde **403** por URL directa | sí |
| La propia fila de usuario | — | se abre en modo lectura: **nadie se edita ni se borra a sí mismo** |
| Sacar un requisito o enlace de la ficha de un trámite | sí (es editar el trámite) | sí |

Todo eso vive en `admin.py` (`SoloSuperusuario`, `SinAutogestion`,
`BaseAdmin`) y está cubierto por `tests/test_admin.py`.

## Rutas

| URL | Vista | Acceso |
|---|---|---|
| `/` | Portada: barra del chatbot + lista de trámites con filtros | público |
| `/tramites/` | Listado con filtros y paginación | público |
| `/tramites/<id>/` | Ficha con requisitos, organismo y botones de enlaces | público |
| `/soporte/` | Formulario de soporte + pedidos del usuario | sesión |
| `/chatbot/` | Asistente (página completa, alternativa sin JS) | público |
| `/chatbot/api/` | JSON que usa la pestaña emergente del chat | público |
| `/buscador/api/` | JSON del asistente para la barra «Buscar» (no guarda la charla) | público |
| `/chatbot/limpiar/` | Vacía la charla de la sesión | sesión (el botón solo se muestra si hay sesión) |
| `/consultas/` | Consultas del usuario (o todas, si es staff) | sesión |
| `/consultas/nueva/` | Formulario de consulta | sesión |
| `/registro/` · `/login/` | Modal de alta y de sesión (también funciona como página) | público |
| `/logout/` | Cierra la sesión (RF-14) | sesión |
| `/perfil/` | Datos personales: nombre, apellido, correo y DNI | sesión |
| `/password/reset/` · `/done/` · `/<uid>/<token>/` · `/complete/` | Recuperar la contraseña olvidada (RF-15) | público |
| `/password/change/` · `/done/` | Cambio de contraseña estando adentro (página propia del sitio) | sesión |
| `/consultas/<id>/` | Detalle de la consulta y respuesta del administrador (RF-10) | sesión |
| `/admin/` | Administración de Django | `is_staff` |
| `/admin/login/` | Login del panel | — |
| `/api/tramites/` | JSON con los trámites | público |

### Piezas del layout

`base.html` lleva la barra (Inicio · Trámites · Soporte + Ingresar) y **dos
pestañas emergentes** que se usan desde cualquier página:

| Modal | Contenido | Se abre |
|---|---|---|
| `#modal-auth` | Pestañas **Ingresar** / **Crear cuenta** | clic en la barra, o solo al llegar a `/login/` y `/registro/` |
| `#modal-chat` | Chat con el asistente | barra de la portada, botón 💬 flotante, o link con `data-abrir="modal-chat"` |

Sin JavaScript todo sigue funcionando: los enlaces caen en `/login/` y
`/registro/` (que abren el mismo modal del lado del servidor) y la barra del
chat manda el POST a `/chatbot/`, que muestra la charla en la página.

Con JavaScript, mientras el modelo local redacta (unos segundos), el modal
muestra la pregunta de una vez y un **«Escribiendo…»** con `aria-live`; al
llegar la respuesta se repinta el historial que devolvió el servidor.

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
├── Dockerfile.ollama                # Ollama + el modelo Qwen ya adentro
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── README.md                       # ← toda la documentación (estás adentro)
├── static/
│   ├── css/app.css                 # hoja de estilos del sitio
│   ├── css/admin.css               # hoja de estilos del panel /admin/
│   └── js/app.js                   # modales + envío del chat (sin frameworks)
└── munitramites/                   # ← TODO lo de Django está acá
    ├── settings.py                 #    configuración: BD, email, chatbot, idioma
    ├── urls.py                     #    rutas: acá se agregan las URL
    ├── wsgi.py / asgi.py           #    puntos de entrada del servidor
    ├── models.py                   #    las tablas de Firebird
    ├── forms.py                    #    validación en el servidor
    ├── admin.py                    #    marca, permisos y qué se ve en /admin/
    ├── context_processors.py       #    form de registro para el modal
    ├── apps.py                     #    identidad de la app + índice del chat
    ├── views/                      #    vistas: UN ARCHIVO POR MÓDULO
    │   ├── __init__.py             #    reexporta todo → las URL no cambian
    │   ├── pagina.py               #    portada
    │   ├── tramites.py             #    listado y ficha
    │   ├── chatbot.py              #    asistente (la lógica está en services/)
    │   ├── consultas.py            #    consultas, sugerencias y detalle
    │   ├── soporte.py              #    soporte
    │   ├── cuenta.py               #    registro y perfil
    │   └── api.py                  #    API JSON
    ├── services/                   #    lógica que no depende del request
    │   └── chatbot/                #    RAG: indexar → recuperar → generar
    │       ├── indexar.py          #    1. convierte trámites en fragmentos
    │       ├── recuperacion.py     #    2. BM25 + sinónimos + stopwords
    │       ├── generacion.py       #    3. plantilla local o LLM (Qwen/Ollama)
    │       └── pipeline.py         #    orquestador + reglas de la charla
    ├── tests/                      #    tests de aceptación (146)
    │   ├── base.py                 #    helpers (usuarios, trámites) + TestCase
    │   ├── test_auth.py            #    ESP-01 · RF-01/02/14/15
    │   ├── test_tramites.py        #    ESP-04/06/07 · RF-07/12
    │   ├── test_chatbot.py         #    asistente: RAG, privacidad y LLM local
    │   ├── test_consultas.py       #    RF-08/09/10
    │   ├── test_roles.py           #    ESP-02 · RF-03/11/13
    │   ├── test_rnf.py             #    RNF-03 rendimiento · RNF-05 integridad
    │   ├── test_tema.py            #    tema claro/oscuro + contraste WCAG
    │   └── test_admin.py           #    cara del panel + candado de permisos
    ├── migrations/                 #    migraciones generadas
    ├── management/commands/
    │   └── cargar_datos.py         #    semilla de datos
    ├── templatetags/
    │   ├── hora.py                 #    filtro |hora_local
    │   └── panel_admin.py          #    {% panel_admin %}: tarjetas del panel
    └── templates/
        ├── base.html               #    layout: barra + los 2 modales
        ├── admin/
        │   ├── base_site.html      #    base de todo el panel: carga admin.css
        │   ├── index.html          #    saludo + tarjetas + atajos
        │   └── panel_resumen.html  #    las tarjetas (las arma panel_admin)
        ├── inicio.html             #    portada (chat + lista con filtros)
        ├── registro.html           #    deja el modal de alta abierto
        ├── soporte.html            #    soporte (solo con sesión)
        ├── chatbot.html            #    asistente en página completa
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
        ├── cuenta/
        │   └── perfil.html         #    nombre, apellido, correo y DNI
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
| Cambiar requisitos o botones de una ficha | `/admin/` → Trámites → **Requisitos** / **Enlaces oficiales** | — |
| Cambiar datos de una cuenta (DNI, correo) | `/admin/` → Usuarios → fila → **Perfil** | — |
| Crear una página nueva | `templates/` + `views/<modulo>.py` + `urls.py` | — |
| Agregar un campo a un formulario | `forms.py` | — |
| Mejorar lo que sabe el asistente | `services/chatbot/` (ver sección siguiente) | — |
| Agregar sinónimos al asistente | `services/chatbot/recuperacion.py` → `SINONIMOS` | — |
| Cambiar el diseño | `static/css/app.css` + `templates/base.html` (del panel: `static/css/admin.css`) | — |
| Agregar un filtro de template | `templatetags/hora.py` | `{% load hora %}` |
| Cargar datos de ejemplo | `management/commands/cargar_datos.py` | `cargar_datos` |
| Correr los tests | `tests/` | `manage.py test --noinput` |
| Cambiar la base de datos | `settings.py` → `DATABASES` | — |
| Cambiar idioma / zona horaria | `settings.py` → `LANGUAGE_CODE` / `TIME_ZONE` | — |
| Cambiar login / redirecciones | `settings.py` → bloque `LOGIN_*` | — |
| Conectar el LLM del chatbot | `settings.py` → `CHATBOT_LLM` | — |
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
docker compose exec web python manage.py shell                  # consola Django
docker compose exec web python manage.py test --noinput         # correr los 146 tests

docker compose --profile llm up -d --build                      # encender el modelo (baja ~4,5 GB)
docker compose exec ollama ollama list                          # modelos cargados (el perfil tiene que estar arriba)
docker compose exec ollama ollama pull qwen2.5:3b               # bajar otro modelo (el perfil también)
docker compose build ollama                                     # (re)armar la imagen con el modelo
docker save munitramites-ollama -o munitramites-ollama.tar      # exportar imagen + modelo
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
`test_roles.AdministradorTests` (alta con el área de acción) y `test_tramites`
(la ficha los muestra), por eso se cita en el archivo y no en esta tabla.

| Documento | Dónde está en el código | Test |
|---|---|---|
| **ESP-01** Autenticación | `forms.py`, `views/cuenta.py`, `templates/registration/` | `test_auth` |
| **ESP-02** Roles | `admin.py`, permisos `is_staff` de Django | `test_roles` · `test_admin` |
| **ESP-04** Administración | `/admin/` (`admin.py`) | `test_roles` · `test_tramites` · `test_admin` |
| **ESP-05** Consultas | `views/consultas.py`, `models.Consulta` | `test_consultas` |
| **ESP-06** Base de datos | Firebird + `models.py` + `migrations/` | todos (corren sobre Firebird) |
| **ESP-07** Interfaz | `templates/`, `static/css/app.css`, sin JS obligatorio | `test_tramites` · `test_chatbot` · `test_admin` · `test_tema` · `test_tramites.ApiTests` |
| **RF-01** Registro de usuario | `views/cuenta.py::registro` (pide DNI) | `test_auth.RegistroTests` · `test_auth.PerfilTests` (editar sus datos) |
| **RF-02** Inicio de sesión | modal de `base.html` + `LoginView` | `test_auth.SesionTests` |
| **RF-03** Gestión de roles | `is_staff` / `is_superuser` | `test_roles` · `test_admin` |
| **RF-07** Administrar trámites | `/admin/` → Trámites (con Requisitos y Enlaces) | `test_roles` · `test_tramites` · `test_admin` |
| **RF-08** Enviar consultas | `views/consultas.py::consulta_nueva` | `test_consultas` |
| **RF-09** Enviar sugerencias | mismo formulario, `tipo = sugerencia` | `test_consultas` |
| **RF-10** Gestionar consultas | `/consultas/<id>/` (respuesta del staff) | `test_consultas.GestionDelAdminTests` |
| **RF-11** Gestionar usuarios | `/admin/` → Usuarios + inline de Perfil (DNI) | `test_roles.AdministradorTests` · `test_admin` |
| **RF-12** Almacenamiento de datos | Firebird vía ORM | todos |
| **RF-13** Control de acceso | `LoginRequired` en cada vista privada | `test_roles.AnonimoTests` · `test_auth.SesionTests` · `test_consultas` · `test_admin.CandadoDelEditorTests` |
| **RF-14** Cerrar sesión | `/logout/` | `test_auth.SesionTests` |
| **RF-15** Recuperar/restablecer contraseña | `urls.py` + `templates/registration/password_reset_*` | `test_auth.RecuperarClaveTests` · `test_auth.PerfilTests` (cambio estando adentro) |
| **IA — precisión contextual** | `services/chatbot/recuperacion.py` (BM25 + umbral) | `test_chatbot.PipelineTests` |
| **IA — alucinaciones** | `services/chatbot/pipeline.py` (`_SIN_INFO`) · `generacion.py` (filtros `_sin_eco` y `_cifras_ajenas`, monto sin indexar sin llamar al modelo) | `test_chatbot` · `test_chatbot.AlucinacionesTests` |
| **IA — cita de fuentes** | `Fragmento.tramite_id` → enlace a la ficha | `test_chatbot` |
| **IA — privacidad** | historial en `request.session`, nada en la BD | `test_chatbot.PrivacidadTests` |
| **IA — barra de búsqueda** | `views/chatbot.py::buscador_api` (mismo `responder()`, sin tocar la sesión) · panel en `lista_tramites.html` + `app.js` | `test_chatbot.BuscadorTests` |
| **IA — modelo local (Qwen/Ollama)** | `generacion.py` (`LLMHttp`) · `settings.CHATBOT_LLM` · `Dockerfile.ollama` | `test_chatbot.PruebaDelLLMTests` |
| **RNF-01** Seguridad | sesión y contraseña de Django (`login_required`, CSRF, hasher), DNI validado y único, «cada uno ve lo suyo» | `test_roles` · `test_admin` · `test_consultas` |
| **RNF-02** Usabilidad | plantillas con `label` y `help_text`, filtros en la portada, formularios con mensajes de error en español | `test_consultas` · `test_tramites` |
| **RNF-03** Rendimiento | `select_related` + `prefetch_related`, 6 por página (`views/tramites.py::POR_PAGINA`), índice BM25 en memoria y cooldown del LLM | `test_rnf.RendimientoTests` (sin N+1 y caché del índice) · `test_tramites.ListadoTests.test_paga_de_a_seis_por_pagina` · `test_chatbot.PruebaDelLLMTests` (cooldown) |
| **RNF-04** Disponibilidad | `restart: unless-stopped`, healthcheck de Firebird y espera activa del `web` en `docker-compose.yml` | — |
| **RNF-05** Integridad | `unique` (Municipio/Organismo), `unique_together` (Requisitos), `PROTECT`/`CASCADE` en las claves foráneas | `test_rnf.IntegridadTests` · `test_auth` |
| **RNF-06** Mantenibilidad | `views/` por módulo, `services/`, docstrings y este README | — |
| **RNF-07** Compatibilidad | el entorno definido del proyecto (Docker) y páginas que andan sin JavaScript ni plugins | `test_chatbot.test_pagina_del_chat_sin_javascript` · `test_chatbot.BuscadorTests.test_el_enlace_sin_javascript_de_verdad_responde` |
| **RNF-08** Escalabilidad | capas independientes (vista ↔ servicio ↔ plantilla) y `INSTALLED_APPS` | — |
| **RNF-09** Despliegue (Docker) | `Dockerfile` + `Dockerfile.ollama` + `docker-compose.yml` | — |
| **RNF-10** Respaldo de BD | sección «Respaldo de la base» más abajo | — |
| **RNF-11** Accesibilidad | `label`, `aria-label`, `aria-modal`, foco visible, sin JS obligatorio, tema claro/oscuro con contraste AA | `test_chatbot` · `test_tema` |

## Asistente virtual (RAG)

El chatbot **no adivina**: arma un índice con los trámites, busca los
fragmentos que responden la pregunta y responde citando de dónde salió.
Tres etapas, tres archivos, todas en `services/chatbot/`. La etapa 3 es la
única que habla con el modelo: **Qwen2.5 corriendo en Ollama, dentro de
Docker** (ver «El modelo: Qwen corriendo en Ollama» más abajo).

| Etapa | Archivo | Qué hace |
|---|---|---|
| 1 · Indexar | `indexar.py` | convierte cada trámite activo en fragmentos (ficha + un fragmento por requisito) con su fuente. Se guarda en memoria y **se invalida solo** cuando cambian trámites, requisitos, municipios u organismos (las señales están en `indexar.py` y se conectan desde `apps.py`) |
| 2 · Recuperar | `recuperacion.py` | normaliza (minúsculas, sin acentos, sin palabras de relleno), expande con `SINONIMOS` (dni → documento, licencia → conducir, …) y puntúa con BM25. Todo lo que queda bajo `CHATBOT_UMBRAL` se descarta |
| 3 · Generar | `generacion.py` | redacta con los fragmentos recuperados: hoy con **Qwen vía `LLMHttp`** (Ollama, local). Si el proveedor no está configurado o falla la red, usa `PlantillaLocal` (sin dependencias ni costo) |
| Orquestador | `pipeline.py` | saludos y ayuda sin buscar, devuelve `{'texto', 'tramites', 'fragmentos'}` y, si no hay contexto, dice explícitamente que no dispone de esa información |

**Se le puede preguntar desde tres lugares**: el modal 💬 (desde cualquier
página), la página `/chatbot/` (con su alternativa sin JS: `/chatbot/?q=…`)
y la **barra de búsqueda del sitio**: lo que se escriba en «Buscar» filtra
la lista y, arriba de los resultados, un panel con el mismo pipeline
redacta la respuesta (`parciales/lista_tramites.html` + `app.js`). Ese
panel sale por `/buscador/api/?q=…`, que llama al mismo `responder()` que
el chat pero **sin tocar la sesión**: lo que se busca no queda en la charla
(privacidad, verificado en vivo). Sin JavaScript el panel muestra el
enlace a `/chatbot/?q=…`, que responde la misma pregunta en el chat.
Tests: `test_chatbot.BuscadorTests`.

### El modelo: Qwen corriendo en Ollama (local)

El asistente redacta con **Qwen2.5** (ligero, ~1 GB) corriendo **en tu PC**,
dentro de un contenedor de Docker: sin API key y sin mandar los datos de
nadie a ningún lado. Ese contenedor está detrás del **perfil `llm`** de
Docker Compose, así que `docker compose up -d` **no lo arma ni descarga
nada**: el modelo se enciende aparte, cuando haya internet.

| Pieza | Dónde está | Qué hace |
|---|---|---|
| Contenedor `ollama` | `docker-compose.yml` (perfil `llm`) + `Dockerfile.ollama` | arma una imagen propia con Ollama **y el modelo ya descargado adentro** |
| Configuración | `settings.py` → `CHATBOT_LLM` | proveedor `ollama`, modelo, URL interna `http://ollama:11434/v1` y `timeout` |
| Cliente HTTP | `services/chatbot/generacion.py` | habla el dialecto OpenAI de Ollama con `urllib`, sin dependencias |
| Respaldo | `generacion.py::PlantillaLocal` | lo que contesta el asistente mientras el modelo no esté disponible |

```powershell
docker compose up -d                         # uso normal: SIN modelo, arranca al toque
docker compose --profile llm up -d --build   # con modelo: baja ~4,5 GB una sola vez
docker compose exec ollama ollama list       # qwen2.5:1.5b aparece ahí
```

**El modelo viaja con la imagen**: se respalda y se mueve con Docker sin
volver a descargar nada (no hay volumen, por eso el modelo no se pierde ni
se tapa).

```powershell
docker save munitramites-ollama -o munitramites-ollama.tar   # exportar
docker load -i munitramites-ollama.tar                       # importar en otra PC
```

Cambiar de modelo (Qwen u otro que hable el dialecto OpenAI):

```yaml
# docker-compose.yml → services.ollama.build.args
args:
  MODELO: qwen2.5:0.5b   # ~400 MB, el más rápido en CPU
  MODELO: qwen2.5:1.5b   # ~1 GB,  el que está por defecto
  MODELO: qwen2.5:3b     # ~2 GB,  más capaz y más lento
```

```powershell
docker compose build ollama                  # baja el modelo nuevo
docker compose --profile llm up -d --build   # y lo deja corriendo
```

**El sitio también tiene que saber el nombre nuevo**:
`munitramites/settings.py` → `CHATBOT_LLM['modelo']` es el modelo que el
cliente le pide a Ollama. Si queda el viejo, Ollama recibe un modelo
inexistente, la llamada falla en silencio y el asistente contesta siempre
con la plantilla local, sin ningún error a la vista.

**Si el modelo no está construido (perfil apagado), el contenedor está
caído o el modelo se pasa del tiempo, la respuesta cae en la plantilla
local**: la conversación nunca se rompe y responde al instante. El prompt
que recibe el modelo (contestar exactamente lo preguntado —sin repetir
siempre la misma fórmula—, responder solo con el contexto, citar el
trámite y admitir cuando no sabe) está en `generacion.py::INSTRUCCION`.

**La respuesta del modelo no se muestra sin pasar por filtros**
(`generacion.py`):

- `_sin_eco` recorta los marcadores «Contexto: … Pregunta: …» si el
  modelo los pegó en vez de contestar,
- `_cifras_ajenas` descarta cualquier cifra que no estuviera en el
  contexto: nunca se le muestra al ciudadano un monto o un plazo
  inventado (pasó en vivo: «$50.000.000» por renovar el DNI),
- las preguntas por **monto** se contestan **sin llamar al modelo** si
  el contexto no trae ninguno: sale un «no dispongo» inmediato y
  determinista, sin gastar los segundos de CPU.

Si un filtro descarta la respuesta, se usa la plantilla local (que tiene
varias redacciones, para que la charla no se vea clonada). Todo eso está
cubierto por `tests/test_chatbot.py::AlucinacionesTests`.

**Cuando la pregunta es corta** («¿y el plazo?») el pipeline la busca
junto con las preguntas anteriores del usuario y le pasa al modelo la
**pregunta previa**, para que sepa de qué habla; las respuestas propias
anteriores no se mandan (un modelo de 1,5 B las copiaba tal cual para
otro trámite). Los casos fijos —saludo, ayuda, «gracias», «chau» y
«limpiar»— responden sin buscar en el índice, y un saludo seguido de una
pregunta ya no se traga la pregunta.

Además, tras un fallo el asistente **no vuelve a tocar la red durante
60 segundos** (`generacion.py::ESPERA_TRAS_UN_FALLO`): sin ese cooldown
cada consulta pagaría la espera del resolver de red (~4 s buscando el
host `ollama` que no existe) para terminar igual en la plantilla. En la
práctica el primer intento cuesta lo que tenga que costar y los
siguientes responden ya.

Si algún día se prefiere un modelo en la nube, alcanza con cambiar
`CHATBOT_LLM` en `settings.py`: `proveedor: 'openai' | 'anthropic' |
'gemini'`, su `api_key` y el `modelo`; no se toca ni la vista ni el RAG.
Y si el sitio corre **fuera de Docker** (en la PC host), cambiar el
`base_url` a `http://localhost:11434/v1`, que es donde se publica el puerto.

Otras perillas: `CHATBOT_TOP_K` (fragmentos que se pasan como contexto) y
`CHATBOT_UMBRAL` (qué tan relevante tiene ser para citarse).

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
- El sitio funciona **sin JavaScript**: los enlaces caen en `/login/` y
  `/registro/` (que abren el modal del lado del servidor) y la barra del chat
  manda el POST a `/chatbot/`.
- El contraste, el orden de tabulación y los tamaños de texto están en
  `static/css/app.css` (incluye `prefers-reduced-motion`). Los pares de color
  de los **dos temas** (claro y oscuro) se calculan contra WCAG AA (4,5:1) en
  `tests/test_tema.py`: si alguien mueve un gris, se entera el test.

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
| `ENLACE` | 0 con el seed | botones con nombre: se cargan en `/admin/`; la ficha muestra igual los `enlace_turnos` / `enlace_oficial` que trae el seed |
| `CONSULTA` | 3+ | seed + formularios (incluye el prefijo `Soporte: `) |
| `PERFIL` | 1+ | se crea con el registro (guarda el DNI) |
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
| Ollama | latest | `Dockerfile.ollama` → imagen propia `munitramites-ollama` |
| Modelo del asistente | `qwen2.5:1.5b` (~1 GB, CPU) | baja en el build de esa imagen |

Credenciales de la base (solo desarrollo): `SYSDBA` / `masterkey`

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
