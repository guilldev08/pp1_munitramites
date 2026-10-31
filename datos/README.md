# `datos/` — base de datos visible

Acá vive el archivo de Firebird que usa el sitio:

```
datos/firebird/munitramites.fdb
```

Es la base **real y en vivo** (no una copia). Docker la monta directo en el
contenedor de Firebird:

> **¿Cómo la veo?** Abrí `datos/COMO_VER_LA_BASE.md` y seguí los pasos
> (extensión Firebird de VS Code ya instalada). Consultas listas en
> `datos/consultas.sql`.
>
> **Diagrama ER:** `datos/esquema.md` (vista previa con `Ctrl+Shift+V`) o
> `datos/esquema.png`. Para un ER interactivo, DBeaver (ya instalado).

```yaml
# docker-compose.yml, servicio firebird
volumes:
  - ./datos/firebird:/var/lib/firebird/data
```

Dentro del contenedor se sigue viendo como
`/var/lib/firebird/data/munitramites.fdb` (eso es lo que dice
`settings.py`); desde Windows la ves en esta carpeta.

- **No la abras con un editor**: el `.fdb` es binario y Firebird lo tiene
  bloqueado mientras el contenedor corre.
- **No la borres ni la reemplaces con el sitio andando.** Si necesitás
  copiarla, parar antes: `docker compose stop firebird web`.
- Los `.fdb` y esta carpeta están en `.gitignore`: no se versionan.
- La carpeta se crea sola al levantar el compose. Si está vacía, Firebird
  crea una base nueva y vacía (perdés los datos).

## El volumen viejo (respaldo)

Hasta octubre de 2026 la base vivía en el volumen nombrado
`munitramites_firebird_data`. Se copió acá y el compose dejó de usarlo,
pero **el volumen sigue existiendo como respaldo**. No lo borres sin
antes comprobar que esta base anda:

```powershell
docker volume ls | Select-String firebird
# volcado del respaldo, por si hace falta
docker run --rm -v munitramites_firebird_data:/from -v "${PWD}\backup:/to" `
  alpine sh -c "cp -a /from/. /to/"
```

Cuando estés seguro de que todo funciona, se puede borrar con
`docker volume rm munitramites_firebird_data`.

## Respaldo normal

```powershell
docker compose exec firebird gbak -b -user SYSDBA -password masterkey `
  /var/lib/firebird/data/munitramites.fdb /tmp/munitramites.fbk
docker compose cp firebird:/tmp/munitramites.fbk .\backup\munitramites.fbk
```
