/* =========================================================================
   Munitramites — comportamiento del sitio.
   Sin dependencias: modales (login/registro y chat) + envío del chatbot.

   Todo lo que se rompe sin JavaScript tiene alternativa:
     · «Ingresar» / «Crear cuenta» → caen en /login/ y /registro/, que
       abren el mismo modal server-side.
     · La barra del chat y el form del modal → mandan POST a /chatbot/
       y la charla se ve en la página completa.

   El modelo corre en la PC y tarda unos segundos: al enviar se pinta la
   pregunta y un «Escribiendo…» con aria-live; al llegar la respuesta,
   pintar() repinta el historial real que devolvió el servidor.
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
     Modales (pestañas emergentes)
     -------------------------------------------------------------------- */
  var scrollGuardado = '';

  function abrir(id, pestana) {
    var modal = document.getElementById(id);
    if (!modal) return;

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
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function enviar(form) {
    var entrada = form.querySelector('input[name=mensaje]');
    var boton = form.querySelector('button[type=submit]');
    var texto = (entrada.value || '').trim();
    if (!texto) return;

    var datos = new FormData();
    datos.append('mensaje', texto);

    boton.disabled = true;

    // El modelo corre en la PC y tarda unos segundos: se pinta la pregunta
    // de una vez y un aviso mientras redacta, así nadie cree que se colgó.
    // aria-live acompaña a los lectores de pantalla; al llegar la respuesta
    // pintar() repinta todo y este aviso desaparece.
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
      .catch(function () {
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
  document.addEventListener('DOMContentLoaded', function () {
    var abierto = $('.modal--abierto');
    if (abierto) document.body.style.overflow = 'hidden';
    if (contChat && contChat.children.length) bajar();
  });
})();
