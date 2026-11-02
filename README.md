# munitramites

Portal de trámites públicos de Misiones: Django + Firebird, todo corriendo
con Docker. Sin frameworks de JavaScript ni build step: Django renderiza HTML
en el servidor y el único JS es `static/js/app.js` (puro, sin dependencias),
que abre los modales, maneja el chat y el tema claro/oscuro.

Qué hace, en corto:

- **Buscador de trámites** con filtros (texto, tema, municipio, modalidad) y
  fichas con requisitos, organismo responsable, documentos descargables y
  enlaces oficiales. La búsqueda tolera tildes, plurales y sinónimos.
- **Asistente virtual** (RAG + Groq) en un modal accesible desde cualquier
  página: guarda el historial por cuenta y cita las fichas de las que habla.
  Sin clave de Groq contesta con plantillas locales, sin gastar la API.
- **Consultas, sugerencias y soporte** que el personal responde y cierra.
- **Tres roles acumulativos** (corriente, administrativo, administrador) con
  panel propio en `/panel/`; `/admin/` de Django queda para el único
  superusuario.
- Registro, sesión, recuperación de contraseña por correo y tema
  claro/oscuro con contraste AA (verificado por tests).

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  instalado y corriendo. No hace falta instalar Python ni Firebird.

## Arrancar

```powershell
docker compose up -d --build
```

| URL | Qué es |
|---|---|
| http://localhost:8000/ | Landing pública (a pantalla completa) |
| http://localhost:8000/tramites/ | Buscador y fichas |
| http://localhost:8000/panel/ | Panel de administración (roles de gestión) |
| http://localhost:8000/admin/ | Admin de Django (solo superusuario) |
| http://localhost:8000/api/tramites/ | API JSON |
| Firebird | puerto 3050 |

La primera vez tarda unos minutos. Otras URLs útiles: `/soporte/`,
`/perfil/`, `/consultas/`, `/login/`, `/registro/` (todas piden sesión
excepto las dos últimas).

**Base de datos:** la base vive en `datos/firebird/munitramites.fdb`, con
138 trámites y 682 requisitos cargados (dataset curado de Misiones). El
comando `cargar_datos` quedó retirado a propósito: **no** vuelve a cargar
datos de ejemplo.

## Usuarios

| Sitio | Quién entra |
|---|---|
| `/panel/` | administrativo, administrador o superusuario |
| `/admin/` de Django | solo el superusuario (a los otros el middleware los manda a `/panel/`) |
| consultas, soporte, perfil | cualquier usuario registrado |

| Rol | Qué puede |
|---|---|
| **Corriente** | ver trámites, preguntarle al asistente, enviar consultas y soporte, editar sus datos |
| **Administrativo** | lo anterior + `/panel/`: responder consultas, editar trámites y temas |
| **Administrador** | lo anterior + cuentas: crear, editar, suspender y borrar usuarios, y cambiar roles |
| **Superusuario** | lo anterior + `/admin/`. **Solo puede haber uno** (lo impone `senales.py`) |

Cuentas ya creadas en desarrollo (todas con clave `Munitra2026!`):

| Usuario | Rol |
|---|---|
| `guilldev08` | superusuario |
| `cuentas` | administrador |
| `gestor` | administrativo |

Las cuentas comunes y de gestión se crean desde `/panel/usuarios/`; el
superusuario, solo así:

```powershell
docker compose exec web python manage.py createsuperuser
```

## Estructura

Todo lo de Django está en una sola carpeta, `munitramites/`:

```
munitramites/
├── static/
│   ├── css/            # app, sitio, landing, tramites, panel, admin, uiverse
│   ├── img/iconos/     # iconos SVG locales (set Lucide)
│   └── js/app.js       # modales + chat + tema (sin frameworks)
└── munitramites/
    ├── settings.py     # BD, email, chatbot, idioma
    ├── urls.py         # rutas
    ├── models.py       # tablas de Firebird
    ├── forms.py        # validación
    ├── admin.py        # cara y permisos de /admin/
    ├── middleware.py   # /admin/ reservado al superusuario
    ├── senales.py      # regla: UN solo superusuario
    ├── views/          # un archivo por módulo (pagina, tramites, chatbot, …)
    ├── services/       # lógica sin request: chatbot/ (RAG), scraper/, busqueda.py
    ├── templatetags/   # {% estatico %}, |hora_local, {% panel_admin %}
    ├── templates/      # base.html, inicio.html, tramites/, panel/, consultas/…
    ├── tests/          # 320 tests de aceptación
    └── management/commands/  # scrapear_sitios
```

### ¿Dónde toco para…?

| Quiero... | Archivo |
|---|---|
| Agregar una ruta o vista | `views/<modulo>.py` + `urls.py` |
| Crear una tabla nueva | `models.py` → `makemigrations` + `migrate` |
| Cambiar el diseño | `static/css/` (el de las fichas, `tramites.css`) |
| Cambiar requisitos de una ficha | `/panel/tramites/` → **Editar** |
| Mejorar lo que sabe el asistente | `services/chatbot/` (sinónimos en `recuperacion.py`) |
| Cambiar CSS o JS | `static/` — referenciar siempre con `{% estatico %}` |
| Agregar un filtro de template | `templatetags/` |
| Ver el payload que va al modelo | `manage.py ver_contexto "¿qué necesito…?"` |

## Comandos útiles

```powershell
docker compose ps                       # estado
docker compose logs -f web              # logs de Django en vivo
docker compose down                     # parar (CONSERVA la base)
docker compose down -v                  # parar y BORRAR la base

docker compose exec web python manage.py check
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test --noinput   # 320 tests
docker compose exec web python manage.py shell            # consola Django
docker compose exec web python manage.py scrapear_sitios  # scraping de sitios oficiales
```

Para correr código desde el host (PowerShell no soporta `<`):

```powershell
Get-Content script.py -Raw | docker compose exec -T web python manage.py shell
```

## Tests

```powershell
docker compose exec web python manage.py test --noinput                    # todos
docker compose exec web python manage.py test munitramites.tests.test_auth --noinput   # un archivo
```

Son **320** y tardan ~2 min porque corren sobre Firebird real; Django crea y
destruye sola la base `munitramites_test.fdb`. Los helpers (usuarios,
trámites) están en `tests/base.py`. Si agregás una funcionalidad, dejá su
test escrito: es lo que hace verificable el sistema.

> En PowerShell el stderr de Docker a veces hace que el comando devuelva
> código 1 aunque todo esté bien: mirá la línea `Ran 320 tests` / `OK`.

## Asistente virtual

La lógica vive en `munitramites/services/chatbot/`, en cuatro pasos:
`indexar.py` convierte los trámites en fragmentos → `recuperacion.py` busca
los relevantes (BM25 + sinónimos) → `generacion.py` redacta → `pipeline.py`
orquesta. El modelo lo corre **Groq** (`llm/groq.py`); la clave va en el
`.env` de la raíz (nunca al repo):

```powershell
# .env, al lado de docker-compose.yml
GROQ_API_KEY=gsk_...
```

```powershell
docker compose up -d web     # aplica el .env
```

Sin clave, sin red o con Groq caído, el asistente contesta igual con las
plantillas locales: nunca inventa datos, y si no sabe lo dice. El modelo no
arma enlaces: los enlaces a las fichas los agrega el servidor.

## Respaldo de la base

> Borrar `datos/firebird/munitramites.fdb` **elimina la base**. Hacé el
> dump antes.

```powershell
# Dump lógico (portable)
docker compose exec firebird gbak -b -user SYSDBA -password masterkey `
  /var/lib/firebird/data/munitramites.fdb /tmp/munitramites.fbk
docker compose cp firebird:/tmp/munitramites.fbk .\munitramites.fbk

# Restaurar
docker compose cp .\munitramites.fbk firebird:/tmp/munitramites.fbk
docker compose exec firebird gbak -c -user SYSDBA -password masterkey `
  /tmp/munitramites.fbk /var/lib/firebird/data/munitramites_restaurada.fdb
```

Para ver la base a mano:

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey `
  localhost:/var/lib/firebird/data/munitramites.fdb   # salir con quit;
```

## Git

| | |
|---|---|
| Repositorio | <https://github.com/guilldev08/pp1_munitramites> |
| Raíz del repo | la carpeta que tiene `manage.py` |
| Rama por defecto | `producción` (`master` sincronizada) |

**Solo existe un `.git`**, el de esa raíz. `.gitignore` deja afuera
`__pycache__/`, `*.fdb`, `.env` y claves, logs y `.vscode/`.

```powershell
git status
git add -A
git commit -m "qué se hizo"
git push
```

## Stack

| Componente | Versión |
|---|---|
| Python | 3.11 (`python:3.11-slim`) |
| Django | 5.2 LTS |
| Firebird | 4.0.7 (`django-firebird` 5.0.4 + `firebird-driver` 2.0.3) |
| Asistente | Groq API (`openai/gpt-oss-120b` por defecto), sin modelo local |

Credenciales de la base (solo desarrollo): `SYSDBA` / `masterkey`.

## Notas

- Idioma `es-ar`, zona horaria `America/Argentina/Buenos_Aires`. Firebird
  guarda sin zona horaria: convertí con el filtro `|hora_local` antes de
  mostrar.
- **Los correos salen por la consola**: el enlace de recuperación de
  contraseña se ve con `docker compose logs web`. En producción va un
  backend SMTP.
- Los contenedores tienen `restart: unless-stopped`.

### Pendiente para producción

`manage.py check --deploy` reporta 6 avisos esperados en desarrollo:
`DEBUG = True` (W018), `SECRET_KEY` de desarrollo (W009), HSTS (W004),
redirect SSL (W008), `SESSION_COOKIE_SECURE` (W012) y
`CSRF_COOKIE_SECURE` (W016). Aparte: `ALLOWED_HOSTS = ['*']` es de
desarrollo y `runserver` hay que reemplazarlo por gunicorn (ya está en
`requirements.txt`).
