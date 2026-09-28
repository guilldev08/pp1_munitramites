# munitramites

Django full stack + Firebird DB, todo corriendo con Docker.

Sin JavaScript de framework, sin build step, sin API intermedia: **Django renderiza
HTML en el servidor, habla con Firebird por ORM y maneja login, formularios y
permisos con sus propios módulos.**

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

No necesitas instalar Python ni Firebird: todo va dentro de los contenedores.

## Arrancar

```powershell
docker compose up -d --build
```

| URL | Qué es |
|---|---|
| http://localhost:8000/ | Sitio público |
| http://localhost:8000/tramites/ | Buscador de trámites |
| http://localhost:8000/admin/ | **Panel de administración (Django)** |
| http://localhost:8000/api/tramites/ | API JSON |
| Firebird | puerto 3050 |

La primera vez tarda unos minutos (baja imágenes e instala dependencias).

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
| Consultas | `/login/` | Cualquier usuario registrado |

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

## Rutas

| URL | Vista | Acceso |
|---|---|---|
| `/` | Portada con destacados y estadísticas | público |
| `/tramites/` | Listado con filtros y paginación | público |
| `/tramites/<id>/` | Ficha con requisitos y organismo | público |
| `/chatbot/` | Asistente que busca en Firebird | público |
| `/consultas/` | Consultas del usuario (o todas, si es staff) | sesión |
| `/consultas/nueva/` | Formulario de consulta | sesión |
| `/registro/` | Alta de usuario | público |
| `/login/` · `/logout/` | Sesión de ciudadanos | — |
| `/password/change/` | Cambio de contraseña | sesión |
| `/admin/` | Administración de Django | `is_staff` |
| `/admin/login/` | Login del panel | — |
| `/api/tramites/` | JSON con los trámites | público |

**No hay catch-all.** Una URL inexistente devuelve el 404 real de Django.

Orden en `urls.py` (importa): admin → auth → páginas → API → estáticos.
Si agregás una ruta nueva, ponla **antes** de la que empiece con `<int:...>`.

## Estructura

Todo lo de Django vive en **una sola carpeta**, `munitramites/`. No hay
subcarpetas raras: entrás ahí y están todos los archivos.

```
munitramites/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── README.md
├── static/
│   └── css/app.css                 # hoja de estilos del sitio
└── munitramites/                   # ← TODO lo de Django está acá
    ├── settings.py                 #    configuración (BD, apps, idioma, login)
    ├── urls.py                     #    rutas: acá se agregan las URL
    ├── views.py                    #    lógica: consulta y guarda en Firebird
    ├── forms.py                    #    validación en el servidor
    ├── models.py                   #    las tablas de Firebird
    ├── admin.py                    #    qué se ve en /admin/
    ├── apps.py                     #    identidad de la app
    ├── tests.py                    #    tests (vacío)
    ├── wsgi.py / asgi.py           #    puntos de entrada del servidor
    ├── migrations/                 #    migraciones generadas
    ├── management/commands/
    │   └── cargar_datos.py         #    semilla de datos
    ├── templatetags/
    │   └── hora.py                 #    filtro |hora_local
    └── templates/
        ├── base.html               #    layout común (header, footer, nav)
        ├── inicio.html             #    portada
        ├── registro.html           #    alta de cuenta
        ├── chatbot.html            #    asistente
        ├── tramites/
        │   ├── lista.html          #    buscador + filtros
        │   └── detalle.html        #    ficha con requisitos
        ├── consultas/
        │   ├── lista.html          #    mis consultas
        │   └── nueva.html          #    formulario
        └── registration/
            └── login.html          #    página de login
```

### ¿Dónde toco para...?

| Quiero... | Archivo | Después |
|---|---|---|
| Agregar una ruta / vista | `urls.py` + `views.py` | — |
| Crear una tabla nueva | `models.py` | `makemigrations` + `migrate` |
| Ver una tabla en `/admin/` | `admin.py` | — |
| Crear una página nueva | `templates/` + `views.py` + `urls.py` | — |
| Agregar un campo a un formulario | `forms.py` | — |
| Cambiar el diseño | `static/css/app.css` + `templates/base.html` | — |
| Agregar un filtro de template | `templatetags/hora.py` | `{% load hora %}` |
| Cargar datos de ejemplo | `management/commands/cargar_datos.py` | `cargar_datos` |
| Cambiar la base de datos | `settings.py` → `DATABASES` | — |
| Cambiar idioma / zona horaria | `settings.py` → `LANGUAGE_CODE` / `TIME_ZONE` | — |
| Cambiar login / redirecciones | `settings.py` → bloque `LOGIN_*` | — |
| Mover el admin de ruta | `urls.py` → línea `path('admin/', ...)` | — |
| Agregar una dependencia | `requirements.txt` | `docker compose up -d --build` |

### El ciclo de trabajo

```
1. models.py       crear la tabla
2. admin.py        registrarla para verla en /admin/
3. forms.py        validar los datos
4. views.py        consultar y guardar
5. templates/      mostrar el resultado
6. urls.py         exponer la ruta
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
docker compose exec web python manage.py test                   # correr tests
```

### Ejecutar código desde el host

PowerShell no soporta `<`, así que se usa pipe:

```powershell
# Opción A: un archivo
Get-Content script.py -Raw | docker compose exec -T web python manage.py shell

# Opción B: una línea
"print(1+1)" | docker compose exec -T web python manage.py shell
```

## Acceder a la base de datos

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey localhost:/var/lib/firebird/data/munitramites.fdb
```

Luego escribí SQL y cerrá con `quit;`.

### Tablas

| Tabla | Registros | Origen |
|---|---|---|
| `MUNICIPIO` | 9 | seed |
| `ORGANISMO` | 7 | seed |
| `TRAMITE` | 8 | seed |
| `REQUISITO` | 32 | seed |
| `CONSULTA` | 3+ | seed + formularios |
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

Credenciales de la base (solo desarrollo): `SYSDBA` / `masterkey`

## Notas

- **Idioma `es-ar`, zona horaria `America/Argentina/Buenos_Aires`.**
- Firebird guarda `TIMESTAMP` sin zona horaria. Con `USE_TZ=True` Django guarda
  en UTC, así que el filtro `|hora_local` (en `templatetags/hora.py`) convierte
  a hora local antes de mostrar. Usalo siempre: `{{ fecha|hora_local|date:"d/m/Y H:i" }}`.
- `settings.py` apunta a `/var/lib/firebird/data/...`, que es la ruta **vista
  desde el servidor Firebird**, no desde tu PC.
- El volumen `firebird_data` guarda la base. Para llevarla a otra PC, hacé un
  dump antes de `docker compose down -v`.
- Los contenedores tienen `restart: unless-stopped`: se levantan solos si Docker
  Desktop se reinicia.

### Pendiente para producción

`manage.py check --deploy` reporta 6 avisos, todos esperados en desarrollo:

| Aviso | Cómo resolverlo |
|---|---|
| `W018 DEBUG=True` | `DEBUG = False` |
| `W009 SECRET_KEY` | generar una clave real y sacarla del repositorio |
| `ALLOWED_HOSTS = ['*']` | listar los dominios reales |
| `W004/W008` HSTS y SSL | poner el sitio detrás de HTTPS |
| `W012/W016` cookies secure | `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` |

Además: `runserver` es el servidor de desarrollo. En producción usar gunicorn
(ya está en `requirements.txt`) o un servidor WSGI equivalente.
