# munitramites

Django + Firebird DB + frontend SPA (React/Vite), todo corriendo con Docker.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

No necesitas instalar Python, Node ni Firebird: todo va dentro de los contenedores.

## Arrancar

```powershell
docker compose up -d --build
```

- Sitio (SPA): http://localhost:8000/
- Panel del sitio: http://localhost:8000/admin/
- Admin nativo de Django: http://localhost:8000/django-admin/
- Firebird: puerto 3050

La primera vez tarda unos minutos (baja imágenes e instala dependencias). Después es inmediato.

## Usuarios

| Sitio | URL | Quién entra |
|---|---|---|
| Panel del sitio | `/admin/` | Cualquier usuario activo de Django |
| Admin nativo | `/django-admin/` | Solo superusuarios (gestionar modelos y usuarios) |

Crear un usuario:

```powershell
docker compose exec web python manage.py createsuperuser
```

O uno normal (sin permisos de superusuario):

```powershell
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model as U; U().objects.create_user('nombre', 'mail@x.com', 'clave')"
```

Cambiar la contraseña:

```powershell
docker compose exec web python manage.py changepassword nombre
```

> **Nota:** la contraseña de Firebird (`SYSDBA` / `masterkey`) es la de la base de
> datos, no tiene nada que ver con los usuarios de Django.

## Rutas

Toda la SPA se sirve desde Django. Las rutas `*` las resuelve React Router en el
cliente, así que cualquier URL desconocida muestra el 404 propio de la SPA.

| URL | Vista |
|---|---|
| `/`, `/tramites`, `/tramites/:id`, `/consultas/nueva`, `/chatbot` | Público |
| `/login`, `/registro` | Público (las del SPA) |
| `/admin`, `/admin/tramites`, `/admin/consultas`, `/admin/usuarios` | Panel (requiere sesión) |
| `/admin/login/`, `/admin/logout/` | Login / logout de Django |
| `/django-admin/` | Admin nativo de Django |
| `/assets/*`, `/locales/*`, `/favicon.ico` | Estáticos del frontend |

Los datos del frontend (trámites, organismos, municipios) van **hardcodeados** en
el bundle: la SPA no llama a ninguna API todavía.

## Comandos útiles

```powershell
docker compose ps                 # estado de los contenedores
docker compose logs -f web        # ver logs de Django en vivo
docker compose down               # parar (CONServa la base de datos)
docker compose down -v            # parar y BORRAR la base de datos
docker compose build --no-cache   # reconstruir desde cero
```

## Acceder a la base de datos

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey localhost:/var/lib/firebird/data/munitramites.fdb
```

Luego escribí SQL y cerrá con `quit;`.

## Estructura

Todo lo de Django vive en **una sola carpeta**, `munitramites/`. No hay
subcarpetas raras: entrás ahí y están todos los archivos.

```
munitramites/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── frontend/                    # SPA compilada con Vite (NO editar a mano)
│   ├── index.html
│   ├── assets/
│   └── locales/
└── munitramites/                # ← TODO lo de Django está acá
    ├── settings.py              #    configuración (base de datos, apps)
    ├── urls.py                  #    rutas: acá se agregan las URL
    ├── views.py                 #    vistas que sirven la SPA
    ├── models.py                #    acá van las tablas de Firebird
    ├── admin.py                 #    qué tablas se ven en /django-admin/
    ├── apps.py                  #    identidad de la app
    ├── tests.py                 #    tests
    ├── wsgi.py / asgi.py        #    puntos de entrada del servidor
    ├── migrations/              #    migraciones generadas
    └── templates/
        └── registration/login.html   # página de login
```

### ¿Dónde toco para...?

| Quiero... | Archivo |
|---|---|
| Agregar una ruta / vista | `munitramites/urls.py` + `munitramites/views.py` |
| Crear una tabla nueva | `munitramites/models.py` → `makemigrations` → `migrate` |
| Ver una tabla en `/django-admin/` | `munitramites/admin.py` |
| Cambiar la base de datos | `munitramites/settings.py` → `DATABASES` |
| Cambiar el login / redirecciones | `munitramites/settings.py` → bloque `LOGIN_*` |
| Cambiar el admin nativo de ruta | `munitramites/urls.py` → línea `django-admin/` |
| Agregar una dependencia | `requirements.txt` → `docker compose up -d --build` |
| Cambiar la SPA | recompilar con Vite y reemplazar `frontend/` |

### Orden de las rutas (importa)

`munitramites/urls.py` se lee de arriba hacia abajo y gana la primera que
coincida. El catch-all de la SPA va **siempre al final**: si metés una URL
debajo, la SPA se la traga y nunca vas a llegar a ella.

`frontend/` es el **build** de la SPA. Si cambiás el código fuente de la SPA,
volvé a compilar con Vite y reemplazá esa carpeta.

## Stack

| Componente | Versión | Imagen |
|---|---|---|
| Python | 3.11 | `python:3.11-slim` |
| Django | 5.2 LTS | (instalado por pip) |
| Backend Firebird | `django-firebird` 5.0.4 | (instalado por pip) |
| Driver | `firebird-driver` 2.0.3 | (instalado por pip) |
| Firebird Server | 4.0.7 | `firebirdsql/firebird:4.0.7` |
| Frontend | React + Vite | (archivos estáticos) |

Credenciales de la base (solo desarrollo): `SYSDBA` / `masterkey`

## Notas

- `settings.py` apunta a `/var/lib/firebird/data/...`, que es la ruta **vista desde
  el servidor Firebird**, no desde tu PC.
- El volumen `firebird_data` guarda la base. Si querés llevar los datos a otra PC,
  hacé un dump antes de `docker compose down -v`.
- `munitramites/4.2` es un archivo vacío sobrante; podés borrarlo sin problema.
