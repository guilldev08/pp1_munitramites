/* =========================================================================
   Munitramites — comportamiento del sitio.
   Sin dependencias: modales (login/registro y chat) + envío del chatbot.

   Todo lo que se rompe sin JavaScript tiene alternativa:
     · «Ingresar» / «Crear cuenta» → caen en /login/ y /registro/, que
       abren el mismo modal server-side (con el sitio detrás).
     · La barra del chat y el form del modal → mandan POST a /chatbot/
       y la charla se ve en la página completa. Sin sesión, el intento
       de escribir abre el modal de login en lugar de fallar.

   Al enviar se pinta la pregunta y un «Escribiendo…» con aria-live;
   al llegar la respuesta, pintar() repinta el historial real que
   devolvió el servidor.
   ========================================================================= */
(function () {
  'use strict';

  /* --------------------------------------------------------------------
     Utilidades
     -------------------------------------------------------------------- */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function elemento(ev) { return ev.target instanceof Element ? ev.target : null; }

  function csrf(form) {
    var campo = form && form.querySelector('[name=csrfmiddlewaretoken]');
    if (campo) return campo.value;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  /* --------------------------------------------------------------------
     Ver / ocultar la contraseña (login, registro y cualquier form de
     clave: cambio y recuperación, alta en el panel…). El botón ya viene
     en el HTML del modal; si un form trae un campo de clave sin botón,
     prepararClaves() lo envuelve y le arma el suyo.
     -------------------------------------------------------------------- */
  function envolverClave(input) {
    if (input.parentNode && input.parentNode.classList.contains('campo__clave')) {
      return input.parentNode;
    }
    var envoltura = document.createElement('span');
    envoltura.className = 'campo__clave';
    input.parentNode.insertBefore(envoltura, input);
    envoltura.appendChild(input);
    return envoltura;
  }

  function botonClave(envoltura) {
    var boton = envoltura.querySelector('[data-ver-clave]');
    if (boton) return boton;
    boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'campo__ver';
    boton.setAttribute('data-ver-clave', '');
    boton.setAttribute('aria-pressed', 'false');
    boton.setAttribute('aria-label', 'Mostrar la contraseña');
    boton.textContent = 'Mostrar';
    envoltura.appendChild(boton);
    return boton;
  }

  function alternarClave(boton) {
    var envoltura = boton.closest('.campo__clave');
    var input = envoltura && envoltura.querySelector('input');
    if (!input) return;
    var mostrando = input.type === 'password';   // el clic la hace visible
    input.type = mostrando ? 'text' : 'password';
    boton.textContent = mostrando ? 'Ocultar' : 'Mostrar';
    boton.setAttribute('aria-pressed', mostrando ? 'true' : 'false');
    boton.setAttribute('aria-label',
      mostrando ? 'Ocultar la contraseña' : 'Mostrar la contraseña');
    input.focus();
  }

  function prepararClaves() {
    $$('input[type="password"]').forEach(function (input) {
      botonClave(envolverClave(input));
    });
  }

  /* --------------------------------------------------------------------
     Modales (pestañas emergentes)
     -------------------------------------------------------------------- */
  var scrollGuardado = '';

  function abrir(id, pestana) {
    var modal = document.getElementById(id);
    if (!modal) return;

    // Un modal por vez: si ya hay otro abierto (el del chat, por
    // ejemplo), se cierra antes de mostrar éste. Sin esto, abrir el de
    // login desde el asistente dejaría los dos apilados.
    $$('.modal--abierto').forEach(function (otro) {
      if (otro !== modal) cerrar(otro);
    });

    modal.classList.add('modal--abierto');
    modal.removeAttribute('hidden');
    document.body.style.overflow = 'hidden';

    if (pestana) seleccionarPestana(modal, pestana);
    if (id === 'modal-auth') prepararNext();

    // Primer campo visible, para escribir de una
    var campo = modal.querySelector('input:not([type=hidden]), textarea');
    if (campo) setTimeout(function () { campo.focus(); }, 60);
  }

  function cerrar(modal) {
    if (!modal) return;
    modal.classList.remove('modal--abierto');
    modal.setAttribute('hidden', '');
    document.body.style.overflow = scrollGuardado;
  }

  function seleccionarPestana(modal, nombre) {
    $$('[data-pestana]', modal).forEach(function (b) {
      b.classList.toggle('activo', b.getAttribute('data-pestana') === nombre);
    });
    $$('[data-panel]', modal).forEach(function (p) {
      p.hidden = p.getAttribute('data-panel') !== nombre;
    });
  }

  // Al entrar desde otra página, «next» apunta a donde estabas parado.
  // En /login/ y /registro/ se respeta el que manda Django (?next=…).
  function prepararNext() {
    var inp = document.getElementById('id_modal_next');
    if (!inp) return;
    var ruta = location.pathname;
    if (ruta === window.MT.urlLogin || ruta === window.MT.urlRegistro) return;
    inp.value = ruta + location.search;
  }

  document.addEventListener('click', function (ev) {
    var el = elemento(ev);
    if (!el) return;

    var botonAbrir = el.closest('[data-abrir]');
    if (botonAbrir) {
      ev.preventDefault();
      abrir(botonAbrir.getAttribute('data-abrir'), botonAbrir.getAttribute('data-tab'));
      return;
    }

    var botonCerrar = el.closest('[data-cerrar]');
    if (botonCerrar) {
      cerrar(botonCerrar.closest('.modal'));
      return;
    }

    var botonVer = el.closest('[data-ver-clave]');
    if (botonVer) {
      alternarClave(botonVer);
      return;
    }

    if (el.classList.contains('modal')) {  // clic en el fondo
      cerrar(el);
      return;
    }

    var tab = el.closest('[data-pestana]');
    if (tab) seleccionarPestana(tab.closest('.modal'), tab.getAttribute('data-pestana'));
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    var abierto = $('.modal--abierto');
    if (abierto) cerrar(abierto);
  });

  /* --------------------------------------------------------------------
     Chatbot: pestaña emergente + barra de la portada
     -------------------------------------------------------------------- */
  var contChat = document.getElementById('chat-historial');

  function bajar() {
    if (contChat) contChat.scrollTop = contChat.scrollHeight;
  }

  function burbuja(texto, rol) {
    var b = document.createElement('div');
    b.className = 'chat__burbuja ' +
      (rol === 'usuario' ? 'chat__burbuja--usuario' : 'chat__burbuja--bot');
    b.textContent = texto;   // texto plano: nada de innerHTML con datos del servidor
    return b;
  }

  function burbujaVacia() {
    var d = document.createElement('div');
    d.className = 'centrado texto-suave';
    d.style.padding = '40px 10px';

    var icono = document.createElement('div');
    icono.textContent = '👋';
    icono.style.fontSize = '2.2rem';
    icono.style.marginBottom = '8px';

    var p1 = document.createElement('p');
    p1.className = 'mb-0';
    p1.textContent = 'Preguntame por cualquier trámite de Misiones.';

    var p2 = document.createElement('p');
    p2.className = 'texto-chico mb-0';
    p2.textContent = 'Ejemplo: «¿qué necesito para la partida de nacimiento?»';

    d.appendChild(icono); d.appendChild(p1); d.appendChild(p2);
    return d;
  }

  function pintar(historial) {
    if (!contChat) return;
    contChat.innerHTML = '';

    if (!historial || !historial.length) {
      contChat.appendChild(burbujaVacia());
      bajar();
      return;
    }

    historial.forEach(function (msg) {
      var b = burbuja(msg.texto || '', msg.rol);
      contChat.appendChild(b);

      if (msg.tramites && msg.tramites.length) {
        b.appendChild(listaTramites(msg.tramites));
      }
    });

    bajar();
  }

  // Enlaces a fichas de trámites: lo comparte el chat y el buscador
  function listaTramites(tramites) {
    var ul = document.createElement('ul');
    ul.className = 'lista-limpia';
    ul.style.marginTop = '10px';
    tramites.forEach(function (t) {
      var li = document.createElement('li');
      li.style.padding = '6px 0';
      li.style.borderTop = '1px dashed var(--gris-200)';
      var a = document.createElement('a');
      a.href = t.url || ('/tramites/' + t.pk + '/');
      a.textContent = '→ ' + t.titulo;
      li.appendChild(a);
      ul.appendChild(li);
    });
    return ul;
  }

  function postChat(datos) {
    return fetch(window.MT.chatApi, {
      method: 'POST',
      body: datos,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf($('form.chat__entrada')) }
    }).then(function (r) {
      if (!r.ok) {
        // El status viaja en el error: el catch distingue el 403
        // (sesión caída) de cualquier otra falla.
        var error = new Error('HTTP ' + r.status);
        error.status = r.status;
        throw error;
      }
      return r.json();
    });
  }

  function enviar(form) {
    var entrada = form.querySelector('input[name=mensaje]');
    var boton = form.querySelector('button[type=submit]');
    var texto = (entrada.value || '').trim();
    if (!texto) return;

    // Sin cuenta no se charla: en vez de mandar un POST que va a doler,
    // se abre el modal de login sobre la página en la que estás parado
    // (con «next» a la página actual, así se vuelve después de entrar).
    if (!window.MT.sesionIniciada) {
      abrir('modal-auth', 'login');
      return;
    }

    var datos = new FormData();
    datos.append('mensaje', texto);

    boton.disabled = true;

    // Se pinta la pregunta de una vez y un aviso mientras el servidor
    // contesta, así nadie cree que se colgó. aria-live acompaña a los
    // lectores de pantalla; al llegar la respuesta pintar() repinta todo
    // y este aviso desaparece.
    var espera = null;
    if (contChat) {
      contChat.appendChild(burbuja(texto, 'usuario'));
      espera = burbuja('Escribiendo…', 'bot');
      espera.setAttribute('aria-live', 'polite');
      espera.setAttribute('aria-busy', 'true');
      contChat.appendChild(espera);
      bajar();
    }

    postChat(datos)
      .then(function (data) {
        entrada.value = '';
        pintar(data.historial);
        abrir('modal-chat');
        var campo = $('#chat-form input[name=mensaje]');
        if (campo) campo.focus();
      })
      .catch(function (err) {
        if (err && err.status === 403) {  // la sesión se cayó en el medio
          abrir('modal-auth', 'login');
          if (contChat) {
            contChat.appendChild(burbuja(
              'Se cerró la sesión: entrá de nuevo para seguir charlando.', 'bot'
            ));
            bajar();
          }
          return;
        }
        abrir('modal-chat');
        if (contChat) {
          contChat.appendChild(burbuja(
            'No pude procesar la pregunta. Probá de nuevo en un momento.', 'bot'
          ));
          bajar();
        }
      })
      .then(function () {
        if (espera && espera.parentNode) espera.parentNode.removeChild(espera);
        boton.disabled = false;
      });
  }

  // Formulario del modal
  var formChat = document.getElementById('chat-form');
  if (formChat) {
    formChat.addEventListener('submit', function (ev) {
      ev.preventDefault();
      enviar(formChat);
    });
  }

  // Barra de la portada: primero abre la pestaña y después manda la pregunta
  var barra = document.getElementById('barra-chat');
  if (barra) {
    barra.addEventListener('submit', function (ev) {
      ev.preventDefault();
      abrir('modal-chat');
      enviar(barra);
    });
  }

  /* --------------------------------------------------------------------
     Barra de búsqueda del sitio: si se escribió algo en «Buscar», la
     consulta también la responde el asistente (mismo pipeline RAG que el
     chat, pero por /buscador/api/ y sin tocar la sesión). Sin JavaScript
     queda el enlace del <noscript> a /chatbot/?q=…
     -------------------------------------------------------------------- */
  var panelBusqueda = document.getElementById('respuesta-ia');
  if (panelBusqueda) {
    var consultaBarra = panelBusqueda.getAttribute('data-consulta') || '';
    var cuerpoBarra = document.getElementById('respuesta-ia-cuerpo');
    if (consultaBarra && cuerpoBarra) {
      fetch(window.MT.buscadorApi + '?q=' + encodeURIComponent(consultaBarra), {
        credentials: 'same-origin'
      })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (data) {
          cuerpoBarra.innerHTML = '';
          cuerpoBarra.appendChild(burbuja(data.texto || '', 'bot'));
          if (data.tramites && data.tramites.length) {
            cuerpoBarra.lastChild.appendChild(listaTramites(data.tramites));
          }
        })
        .catch(function () {
          cuerpoBarra.innerHTML = '';
          var aviso = document.createElement('p');
          aviso.className = 'mb-0';
          aviso.textContent = 'No pude consultar al asistente. ';
          var enlace = document.createElement('a');
          enlace.href = window.MT.urlChat + '?q=' + encodeURIComponent(consultaBarra);
          enlace.textContent = 'Intentar en el chat →';
          aviso.appendChild(enlace);
          cuerpoBarra.appendChild(aviso);
        });
    }
  }

  // Botón «Vaciar chat»
  var limpiar = document.getElementById('chat-limpiar');
  if (limpiar) {
    limpiar.addEventListener('click', function () {
      var datos = new FormData();
      datos.append('accion', 'limpiar');
      limpiar.disabled = true;
      postChat(datos)
        .then(function (data) { pintar(data.historial); })
        .catch(function () { /* se queda como estaba */ })
        .then(function () { limpiar.disabled = false; });
    });
  }

  /* --------------------------------------------------------------------
     Tema claro / oscuro (el atributo data-tema lo pone base.html antes
     de pintar; acá solo se voltea y se recuerda la elección)
     -------------------------------------------------------------------- */
  var botonTema = document.getElementById('cambiar-tema');

  function temaActual() {
    return document.documentElement.getAttribute('data-tema') || 'claro';
  }

  function pintarTema() {
    if (!botonTema) return;
    var oscuro = temaActual() === 'oscuro';
    botonTema.textContent = oscuro ? '☀️' : '🌙';
    botonTema.setAttribute('aria-pressed', oscuro ? 'true' : 'false');
    botonTema.setAttribute('aria-label',
      oscuro ? 'Cambiar al tema claro' : 'Cambiar al tema oscuro');
    botonTema.setAttribute('title', oscuro ? 'Tema claro' : 'Tema oscuro');
  }

  if (botonTema) {
    botonTema.addEventListener('click', function () {
      var siguiente = temaActual() === 'oscuro' ? 'claro' : 'oscuro';
      document.documentElement.setAttribute('data-tema', siguiente);
      try { localStorage.setItem('munitramites-tema', siguiente); } catch (e) {}
      pintarTema();
    });
    pintarTema();
  }

  /* --------------------------------------------------------------------
      Arranque
      -------------------------------------------------------------------- */
  /* --------------------------------------------------------------------
     Filas de los formsets del panel (+ Agregar requisito/enlace/dirección):
     clonan la plantilla <template data-vacio="..."> y suben TOTAL_FORMS.
     Además numeran las filas visibles (data-numerar) y sacan de la lista
     la fila marcada «Eliminar», con un «Deshacer» para volver atrás.
     -------------------------------------------------------------------- */
  function filasDe(contenedor) {
    return $$('.inline-fila', contenedor);
  }

  function casillaBorrar(fila) {
    return fila.querySelector('input[type="checkbox"][name$="-DELETE"]');
  }

  function numerarFilas(contenedor) {
    if (!contenedor.hasAttribute('data-numerar')) return;
    var numero = 0;
    filasDe(contenedor).forEach(function (fila) {
      if (fila.classList.contains('inline-fila--oculta')) return;
      numero += 1;
      var salida = fila.querySelector('[data-numero]');
      if (salida) salida.textContent = String(numero);
    });
  }

  function avisoDeBorrado(contenedor) {
    var panel = contenedor.parentNode;
    return panel ? panel.querySelector('[data-aviso-borrado]') : null;
  }

  function refrescarAviso(contenedor) {
    var aviso = avisoDeBorrado(contenedor);
    if (!aviso) return;
    var marcadas = filasDe(contenedor).filter(function (fila) {
      var box = casillaBorrar(fila);
      return box && box.checked;
    }).length;
    aviso.hidden = !marcadas;
    if (!marcadas) return;
    var singular = aviso.getAttribute('data-aviso-borrado') || 'fila';
    var plural = aviso.getAttribute('data-aviso-plural') || singular + 's';
    var texto = aviso.querySelector('[data-texto]');
    if (texto) {
      texto.textContent = marcadas === 1
        ? '1 ' + singular + ' para eliminar.'
        : marcadas + ' ' + plural + ' para eliminar.';
    }
  }

  function sacarFila(fila, contenedor) {
    var box = casillaBorrar(fila);
    fila.classList.toggle('inline-fila--oculta', !!(box && box.checked));
    numerarFilas(contenedor);
    refrescarAviso(contenedor);
  }

  function prepararFilas(contenedor) {
    filasDe(contenedor).forEach(function (fila) {
      var box = casillaBorrar(fila);
      if (box && !box.hasAttribute('data-preparada')) {
        box.setAttribute('data-preparada', '');
        box.addEventListener('change', function () {
          sacarFila(fila, contenedor);
        });
      }
      sacarFila(fila, contenedor);
    });

    var aviso = avisoDeBorrado(contenedor);
    var deshacer = aviso && aviso.querySelector('[data-deshacer]');
    if (deshacer && !deshacer.hasAttribute('data-preparado')) {
      deshacer.setAttribute('data-preparado', '');
      deshacer.addEventListener('click', function (ev) {
        ev.preventDefault();
        filasDe(contenedor).forEach(function (fila) {
          var box = casillaBorrar(fila);
          if (box) box.checked = false;
          fila.classList.remove('inline-fila--oculta');
        });
        numerarFilas(contenedor);
        refrescarAviso(contenedor);
      });
    }
  }

  function prepararInlines() {
    $$('[data-filas]').forEach(function (contenedor) {
      var clave = contenedor.getAttribute('data-filas');
      var boton = $('[data-agregar-fila="' + clave + '"]');
      var plantilla = $('[data-vacio="' + clave + '"]');
      var management = $('[name="' + clave + '-TOTAL_FORMS"]');

      prepararFilas(contenedor);
      numerarFilas(contenedor);
      refrescarAviso(contenedor);

      if (!boton || !plantilla || !management) return;
      boton.addEventListener('click', function (ev) {
        ev.preventDefault();
        var n = parseInt(management.value, 10) || 0;
        contenedor.insertAdjacentHTML(
          'beforeend',
          plantilla.innerHTML.replace(/__prefix__/g, String(n))
        );
        management.value = n + 1;
        prepararFilas(contenedor);
      });
    });
  }

  /* --------------------------------------------------------------------
     Marcar / desmarcar todas las filas del listado del panel.
     -------------------------------------------------------------------- */
  function prepararMarcaTotal() {
    var maestro = $('[data-marcar-todo]');
    if (!maestro) return;
    maestro.addEventListener('change', function () {
      $$('[name="seleccion"]').forEach(function (box) {
        box.checked = maestro.checked;
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    prepararClaves();
    prepararInlines();
    prepararMarcaTotal();
    var abierto = $('.modal--abierto');
    if (abierto) document.body.style.overflow = 'hidden';
    if (contChat && contChat.children.length) bajar();
  });
})();
