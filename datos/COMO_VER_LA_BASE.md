# Cómo ver la base desde VS Code

El `.fdb` **no se abre como un archivo**: es binario y solo lo entiende el
motor de Firebird. Lo que se hace es **conectarse al servidor** Firebird que
ya corre en Docker y consultarlo con SQL.

## Ya está instalado

Extensión de VS Code: **Firebird SQL** (`wdtbrchan.firebird-vscode`).

Después de instalarla, recargá la ventana una vez:
`Ctrl+Shift+P` → **Developer: Reload Window**. Después te aparece un ícono
de Firebird en la barra lateral izquierda.

> La extensión `cweijan.vscode-database-client2` que ya tenías no sirve para
> Firebird. La `marinv.vscode-db-explorer-firebird` está abandonada y rota.

## Crear la conexión

1. Clic en el ícono de **Firebird** en la barra de actividad.
2. Clic en **`+`** (New Connection) en la vista *Databases*.
3. Completá:

| Campo | Valor |
|---|---|
| Nombre | `Munitramites local` |
| Host | `localhost` |
| Puerto | `3050` |
| Base de datos | `/var/lib/firebird/data/munitramites.fdb` |
| Usuario | `SYSDBA` |
| Contraseña | `masterkey` |
| Charset | `UTF8` |

> La ruta de la base es la que ve **el servidor Firebird**, no la de Windows.
> Por eso empieza con `/var/lib/firebird/...` aunque el archivo esté en
> `datos/firebird/munitramites.fdb`.

Si el campo "Database" pide el formato completo, probá:

```
localhost/3050:/var/lib/firebird/data/munitramites.fdb
```

## Consultar

Abrí `datos/consultas.sql`, poné el cursor en una consulta y apretá
**`Ctrl+Enter`**. Los resultados salen en un panel aparte.

Los nombres de tablas y columnas van **en MAYÚSCULAS** (así los creó Django):

```sql
SELECT ID, TITULO FROM MUNITRAMITES_TRAMITE;
```

## Si no conecta

1. Que Docker esté arriba: `docker compose up -d`.
2. Que el puerto escuche: `Test-NetConnection localhost -Port 3050`.
3. Mirá el log de la extensión: `Ctrl+Shift+P` →
   **Firebird: Show Firebird SQL Log**.
4. Si el puerto está tomado o cerrado: `docker compose logs firebird`.

## Diagrama ER (lo que pediste)

Hay dos formas de verlo como diagrama:

### 1. Rápido, ya generado (sin instalar nada más)

Abrí `datos/esquema.md` y apretá `Ctrl+Shift+V`. El diagrama Mermaid se
dibuja en la vista previa. También está la imagen `datos/esquema.png`.

### 2. DBeaver (visor de base completo, con ER interactivo)

Ya está instalado **DBeaver Community** (menú Inicio → DBeaver).

1. `Database` → `New Database Connection` → **Firebird**.
2. Completá con los mismos datos de la tabla de arriba
   (host `localhost`, puerto `3050`, base
   `/var/lib/firebird/data/munitramites.fdb`, `SYSDBA` / `masterkey`).
3. La primera vez DBeaver baja el driver JDBC de Firebird (necesita
   internet); aceptá.
4. Para el diagrama: en el **Database Navigator**, desplegá la conexión →
   clic derecho sobre **Tables** → **View Diagram**.
   También podés abrir una tabla (doble clic) y usar la pestaña
   **ER Diagram**, o seleccionar varias tablas → clic derecho →
   **Show in ER Diagram**.

Es un diagrama interactivo: arrastrás tablas, ves las relaciones y podés
exportarlo como imagen.

## Alternativa sin extensión

Cualquier cliente Firebird sirve con los mismos datos: **DBeaver** (gratis,
recomendado), FlameRobin o la consola `isql` del contenedor:

```powershell
docker compose exec firebird isql -user SYSDBA -password masterkey `
  localhost:/var/lib/firebird/data/munitramites.fdb
```
