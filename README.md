# Munitramites

Portal web con la información de los trámites públicos de la provincia de
Misiones: qué papeles se necesitan, dónde se hace cada uno y con qué
organismo hay que hablar.

## ¿Qué hace?

- **Busca trámites** por tema, municipio o modalidad (presencial, digital o
  mixta) y muestra una ficha con los requisitos, el organismo responsable y
  los enlaces oficiales.
- **Responde preguntas** con un asistente que cita el trámite del que saca
  cada dato. Si no sabe, lo aclara en lugar de inventar.
- **Recibe consultas, sugerencias y reclamos** de la gente, y permite seguir
  la respuesta.
- **Administra el contenido** desde un panel privado: cargar y editar
  trámites, crear temas y responder lo que llega.

## ¿Para qué sirve?

Para que la gente pierda menos tiempo y menos viajes: toda la información de
un trámite está en un solo lugar, actualizada y en lenguaje simple. Del otro
lado, le da al organismo una sola herramienta para publicar los trámites y
atender lo que la gente pregunta.

## Cómo ejecutarla

Solo hace falta tener [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado y abierto. No hay que instalar Python ni bases de datos: todo corre
dentro de Docker.

```powershell
git clone https://github.com/guilldev08/pp1_munitramites.git
cd pp1_munitramites
git switch feature/frontend
docker compose up -d --build
```

La primera vez tarda unos minutos. Cuando termina, la página queda en:

**http://localhost:8000/**

La base arranca vacía. Para cargar los trámites de ejemplo y crear la cuenta
de administrador:

```powershell
docker compose exec web python manage.py cargar_datos
docker compose exec web python manage.py createsuperuser
```

Después se entra con esa cuenta y el panel de administración está en
**http://localhost:8000/panel/**.

Para apagar todo:

```powershell
docker compose down
```

## Captura

<img src="docs/img/captura-pagina-publica.png" width="720" alt="Captura de la página pública de Munitramites">
