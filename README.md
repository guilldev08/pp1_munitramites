# munitramites

Django + Firebird DB, corriendo con Docker.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo

No necesitas instalar Python ni Firebird: ambos van dentro de los contenedores.

## Arrancar

```powershell
docker compose up -d --build
```

- App: http://localhost:8000/admin/
- Firebird: puerto 3050

La primera vez tarda unos minutos (baja imágenes e instala dependencias). Después es inmediato.

## Crear un usuario admin

```powershell
docker compose exec web python manage.py createsuperuser
```

## Comandos útiles

```powershell
docker compose ps              # estado de los contenedores
docker compose logs -f web     # ver logs de Django en vivo
docker compose down            # parar (CONServa la base de datos)
docker compose down -v         # parar y BORRAR la base de datos
docker compose build --no-cache  # reconstruir desde cero
```

## Acceder a la base de datos

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey localhost:/var/lib/firebird/data/munitramites.fdb
```

Luego escribí SQL y cerrá con `quit;`.

## Stack

| Componente | Versión | Imagen |
|---|---|---|
| Python | 3.11 | `python:3.11-slim` |
| Django | 5.2 LTS | (instalado por pip) |
| Backend Firebird | `django-firebird` 5.0.4 | (instalado por pip) |
| Driver | `firebird-driver` 2.0.3 | (instalado por pip) |
| Firebird Server | 4.0.7 | `firebirdsql/firebird:4.0.7` |

Credenciales por defecto (solo desarrollo): `SYSDBA` / `masterkey`

## Notas

- `settings.py` apunta a `/var/lib/firebird/data/...`, que es la ruta **vista desde el
  servidor Firebird**, no desde tu PC.
- El volumen `firebird_data` guarda la base. Si querés llevar los datos a otra PC,
  hacé un dump antes de `docker compose down -v`.
