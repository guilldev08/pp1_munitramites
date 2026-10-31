# Esquema de la base (diagrama ER)

Generado a partir de la base real (`datos/firebird/munitramites.fdb`).
Refleja las tablas del dominio y sus claves foráneas.

- `PK` = clave primaria.
- Las líneas `||--o{` son relaciones uno-a-muchos (una fila de la izquierda
  puede tener muchas de la derecha).
- Las tablas de Django (`DJANGO_*`, `AUTH_*` internas) se omiten salvo
  `AUTH_USER`, que es la cuenta de usuario.
- `PERFIL` es la extensión de `AUTH_USER` que guarda el rol.

![Diagrama ER](esquema.png)

Para verlo renderizado en VS Code: abrí este archivo y apretá `Ctrl+Shift+V`
(vista previa). La extensión **Markdown Preview Mermaid Support** ya está
instalada, así que el bloque de abajo se dibuja solo.

```mermaid
erDiagram
    AUTH_USER {
        int ID PK
        varchar PASSWORD
        datetime LAST_LOGIN
        boolean IS_SUPERUSER
        varchar USERNAME
        varchar FIRST_NAME
        varchar LAST_NAME
        varchar EMAIL
        boolean IS_STAFF
        boolean IS_ACTIVE
        datetime DATE_JOINED
    }
    PERFIL {
        char ID PK
        datetime CREADO
        datetime ACTUALIZADO
        varchar ROL
        int USER_ID
    }
    MUNICIPIO {
        bigint ID PK
        varchar NOMBRE
    }
    ORGANISMO {
        bigint ID PK
        varchar NOMBRE
        varchar DIRECCION
        varchar OCUPACION
        varchar SITIO
    }
    TEMA {
        bigint ID PK
        varchar NOMBRE
    }
    TRAMITE {
        bigint ID PK
        varchar TITULO
        varchar MODALIDAD
        blob DESCRIPCION
        varchar ENLACE_TURNOS
        varchar ENLACE_OFICIAL
        boolean DESTACADO
        boolean ACTIVO
        datetime CREADO
        datetime ACTUALIZADO
        bigint MUNICIPIO_ID
        bigint ORGANISMO_ID
        bigint TEMA_ID
    }
    REQUISITO {
        bigint ID PK
        varchar DESCRIPCION
        int ORDEN
        bigint TRAMITE_ID
    }
    ENLACE {
        bigint ID PK
        varchar NOMBRE
        varchar URL
        int ORDEN
        bigint TRAMITE_ID
    }
    DIRECCION {
        bigint ID PK
        varchar LUGAR
        varchar DIRECCION
        bigint MUNICIPIO_ID
        bigint TRAMITE_ID
    }
    ARCHIVOTRAMITE {
        bigint ID PK
        varchar TITULO
        varchar TIPO
        varchar ARCHIVO
        varchar DESCRIPCION
        int ORDEN
        bigint TRAMITE_ID
    }
    CONSULTA {
        bigint ID PK
        varchar TIPO
        varchar ASUNTO
        blob CONTENIDO
        varchar ESTADO
        blob RESPUESTA
        datetime FECHA
        int USUARIO_ID
        bigint TRAMITE_ID
    }
    CONVERSACIONCHAT {
        bigint ID PK
        varchar TITULO
        datetime CREADO
        datetime ACTUALIZADO
        int USUARIO_ID
    }
    MENSAJECHAT {
        bigint ID PK
        varchar ROL
        blob TEXTO
        datetime CREADO
        bigint CONVERSACION_ID
    }
    FUENTEMENSAJE {
        bigint ID PK
        varchar TITULO
        int ORDEN
        bigint TRAMITE_ID
        bigint MENSAJE_ID
    }
    AUTH_USER ||--o{ PERFIL : "USER_ID"
    MUNICIPIO ||--o{ TRAMITE : "MUNICIPIO_ID"
    ORGANISMO ||--o{ TRAMITE : "ORGANISMO_ID"
    TEMA ||--o{ TRAMITE : "TEMA_ID"
    TRAMITE ||--o{ REQUISITO : "TRAMITE_ID"
    TRAMITE ||--o{ ENLACE : "TRAMITE_ID"
    MUNICIPIO ||--o{ DIRECCION : "MUNICIPIO_ID"
    TRAMITE ||--o{ DIRECCION : "TRAMITE_ID"
    TRAMITE ||--o{ ARCHIVOTRAMITE : "TRAMITE_ID"
    AUTH_USER ||--o{ CONSULTA : "USUARIO_ID"
    TRAMITE ||--o{ CONSULTA : "TRAMITE_ID"
    AUTH_USER ||--o{ CONVERSACIONCHAT : "USUARIO_ID"
    CONVERSACIONCHAT ||--o{ MENSAJECHAT : "CONVERSACION_ID"
    TRAMITE ||--o{ FUENTEMENSAJE : "TRAMITE_ID"
    MENSAJECHAT ||--o{ FUENTEMENSAJE : "MENSAJE_ID"
```
