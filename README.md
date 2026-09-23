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

```
munitramites/
├── Dockerfile
├── Docker-compose.yml
├── requirements.txt
├── manage.py
├── frontend/                  # SPA compilada con Vite (NO editar a mano)
│   ├── index.html
│   ├── assets/
│   └── locales/
├── templates/
│   └── registration/login.html # página de login de Django
└── munitramites/
    ├── settings.py
    ├── urls.py                 # rutas: auth + admin + estáticos + catch-all SPA
    └── views.py                # vistas que sirven la SPA
```

`frontend/` es el **build** de la SPA. Si cambias el código fuente de la SPA,
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
