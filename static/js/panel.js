/* =========================================================================
   Munitramites · Tablero del panel (/panel/)
   Refresca solo el contenido de los gráficos cuando cambian los filtros.
   Sin JavaScript el formulario hace un GET normal y la página se recarga.
   ========================================================================= */
(function () {
  'use strict';

  var form = document.querySelector('[data-pn-filtros]');
  var contenedor = document.getElementById('pn-dashboard-contenido');
  if (!form || !contenedor) return;

  var urlDatos = form.getAttribute('data-url') || form.action;
  var aviso = form.querySelector('[data-pn-cargando]');
  var enCurso = 0;

  function parametros() {
    var datos = new FormData(form);
    var params = new URLSearchParams();
    datos.forEach(function (valor, clave) {
      if (valor !== '' && valor !== null) params.append(clave, valor);
    });
    return params;
  }

  function mostrarCarga(activo) {
    form.setAttribute('aria-busy', activo ? 'true' : 'false');
    if (aviso) aviso.hidden = !activo;
  }

  function actualizar() {
    var params = parametros();
    var turno = ++enCurso;
    mostrarCarga(true);

    fetch(urlDatos + '?' + params.toString(), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (respuesta) {
        if (!respuesta.ok) throw new Error('No se pudo actualizar');
        return respuesta.text();
      })
      .then(function (html) {
        if (turno !== enCurso) return;
        contenedor.outerHTML = html;
        contenedor = document.getElementById('pn-dashboard-contenido');
        var consulta = params.toString();
        var destino = form.action + (consulta ? '?' + consulta : '');
        if (window.history && window.history.replaceState) {
          window.history.replaceState(null, '', destino);
        }
      })
      .catch(function () {
        // Si el fetch falla, la misma URL funciona como página completa.
        window.location.href = form.action + '?' + params.toString();
      })
      .finally(function () {
        if (turno === enCurso) mostrarCarga(false);
      });
  }

  form.addEventListener('submit', function (evento) {
    evento.preventDefault();
    actualizar();
  });

  form.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo || !campo.name) return;

    var esFecha = campo.type === 'date';
    if (esFecha) {
      var periodo = form.querySelector('[name="periodo"]');
      if (periodo && (form.desde.value || form.hasta.value)) {
        periodo.value = 'personalizado';
      }
    } else if (campo.name === 'periodo' && campo.value !== 'personalizado') {
      form.desde.value = '';
      form.hasta.value = '';
    }
    actualizar();
  });
})();
