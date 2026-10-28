/* =========================================================================
   Munitramites — comportamiento del sitio.
   Sin dependencias: modales (login/registro y chat) + envío del chatbot.

   Todo lo que se rompe sin JavaScript tiene alternativa:
     · «Ingresar» / «Crear cuenta» → caen en /login/ y /registro/, que
       abren el mismo modal server-side (con el sitio detrás).
     · El modal del asistente y la barra del chat funcionan con
       JavaScript: abren la pestaña y mandan la pregunta por JSON. Sin
       sesión, el intento de escribir abre el modal de login.

   Al enviar se pinta la pregunta y un «Escribiendo…» con aria-live;
   al llegar la respuesta, pintar() repinta el historial real que
   devolvió el servidor. El modal recuerda la conversación activa, la
   posición del scroll, el borrador y si la barra lateral estaba abierta
   (sessionStorage), y se limpia al cerrar sesión.
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

    if (id === 'modal-chat') {
      estadoChat.abierto = true;
      guardarEstadoChat();
      if (estadoChat.panel) abrirPanel(); else cerrarPanel();
    }

    // Primer campo visible, para escribir de una
    var campo = modal.querySelector('input:not([type=hidden]), textarea');
    if (campo) setTimeout(function () { campo.focus(); }, 60);

    // El modal vive en todas las páginas: al abrirlo por primera vez
    // trae la conversación activa (y la lista completa para cambiar).
    if (id === 'modal-chat' && window.MT.sesionIniciada && !chatCargado) {
      cargarChat(conversacionActual);
    }
  }

  function cerrar(modal) {
    if (!modal) return;
    if (modal.id === 'modal-chat') {
      guardarScroll();
      guardarBorrador();
      estadoChat.abierto = false;
      guardarEstadoChat();
    }
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
      var destino = botonAbrir.getAttribute('data-abrir');
      abrir(destino, botonAbrir.getAttribute('data-tab'));
      if (destino === 'modal-chat') {
        prefillChat(botonAbrir.getAttribute('data-chat-pregunta'));
      }
      return;
    }

    var cerrarPanelBtn = el.closest('[data-cerrar-panel]');
    if (cerrarPanelBtn) {
      ev.preventDefault();
      cerrarPanel();
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
    var modalChat = document.getElementById('modal-chat');
    var chatVisible = modalChat &&
      modalChat.classList.contains('modal--abierto');
    if (chatVisible && panelAbierto()) {
      cerrarPanel();
      return;
    }
    var abierto = $('.modal--abierto');
    if (abierto) cerrar(abierto);
  });

  /* --------------------------------------------------------------------
     Chatbot: pestaña emergente + barra de la portada
     -------------------------------------------------------------------- */
  var contChat = document.getElementById('chat-historial');
  var listaChat = document.getElementById('chat-lista');
  var panelChat = document.getElementById('chat-panel');
  var fondoPanel = document.getElementById('chat-panel-fondo');
  var botonHamburguesa = document.getElementById('chat-hamburguesa');
  var entradaChat = document.getElementById('chat-mensaje');
  var conversacionActual = '';
  var chatCargado = false;
  var cargaChatToken = 0;

  // Persistencia del modal en la pestaña: misma conversación, scroll,
  // borrador y barra lateral al cerrar y volver a abrir, incluso después
  // de navegar a otra página. Se guarda por usuario y se borra al salir.
  var CLAVE_CHAT = 'mt-chat:' + (window.MT.usuarioId || 'anon');
  var estadoChat = {
    conversacion: '',
    abierto: false,
    panel: false,
    scroll: {},
    borradores: {}
  };

  function leerEstadoChat() {
    try {
      var crudo = sessionStorage.getItem(CLAVE_CHAT);
      if (!crudo) return;
      var datos = JSON.parse(crudo);
      if (!datos || typeof datos !== 'object') return;
      estadoChat.conversacion = datos.conversacion
        ? String(datos.conversacion) : '';
      estadoChat.abierto = !!datos.abierto;
      estadoChat.panel = !!datos.panel;
      estadoChat.scroll = (
        datos.scroll && typeof datos.scroll === 'object'
      ) ? datos.scroll : {};
      estadoChat.borradores = (
        datos.borradores && typeof datos.borradores === 'object'
      ) ? datos.borradores : {};
    } catch (e) { /* sessionStorage puede estar bloqueado */ }
  }

  function guardarEstadoChat() {
    try {
      sessionStorage.setItem(CLAVE_CHAT, JSON.stringify(estadoChat));
    } catch (e) { /* sin persistencia, el modal sigue andando */ }
  }

  function limpiarEstadosChat(conservar) {
    try {
      Object.keys(sessionStorage).forEach(function (clave) {
        if (clave.indexOf('mt-chat:') === 0 && clave !== conservar) {
          sessionStorage.removeItem(clave);
        }
      });
    } catch (e) { /* nada que limpiar */ }
  }

  function claveConversacion() {
    return conversacionActual || 'nueva';
  }

  function bajar() {
    if (!contChat) return;
    contChat.scrollTop = contChat.scrollHeight;
    estadoChat.scroll[claveConversacion()] = contChat.scrollTop;
    guardarEstadoChat();
  }

  function restaurarScroll() {
    if (!contChat) return;
    var guardado = estadoChat.scroll[claveConversacion()];
    if (typeof guardado !== 'number') {
      bajar();
      return;
    }
    requestAnimationFrame(function () {
      contChat.scrollTop = guardado;
    });
  }

  function guardarScroll() {
    if (!contChat) return;
    estadoChat.scroll[claveConversacion()] = contChat.scrollTop;
    guardarEstadoChat();
  }

  function cargarBorrador() {
    if (!entradaChat) return;
    entradaChat.value = estadoChat.borradores[claveConversacion()] || '';
  }

  function guardarBorrador() {
    if (!entradaChat) return;
    estadoChat.borradores[claveConversacion()] = entradaChat.value;
    guardarEstadoChat();
  }

  function prefillChat(texto) {
    if (!entradaChat || !texto) return;
    entradaChat.value = texto;
    estadoChat.borradores[claveConversacion()] = texto;
    guardarEstadoChat();
    setTimeout(function () { entradaChat.focus(); }, 60);
  }

  function burbuja(texto, rol, segmentos) {
    var b = document.createElement('div');
    b.className = 'chat__burbuja ' +
      (rol === 'usuario' ? 'chat__burbuja--usuario' : 'chat__burbuja--bot');

    // El servidor manda los segmentos ya escapados: texto plano y, si
    // corresponde, el enlace interno de la ficha. Nunca innerHTML.
    if (rol !== 'usuario' && segmentos && segmentos.length) {
      segmentos.forEach(function (seg) {
        if (seg.url) {
          var a = document.createElement('a');
          a.href = seg.url;
          a.textContent = seg.texto;
          a.title = 'Abrir la ficha en el sistema';
          b.appendChild(a);
        } else {
          b.appendChild(document.createTextNode(seg.texto || ''));
        }
      });
    } else {
      b.textContent = texto;
    }
    return b;
  }

  function burbujaVacia() {
    var d = document.createElement('div');
    d.className = 'centrado texto-suave chat__vacio';

    var icono = document.createElement('div');
    icono.className = 'chat__vacio-icono';
    icono.textContent = '👋';

    var p1 = document.createElement('p');
    p1.className = 'mb-0';
    p1.textContent = 'Preguntame por cualquier trámite de Misiones.';

    var p2 = document.createElement('p');
    p2.className = 'texto-chico mb-0';
    p2.textContent = 'Ejemplo: «¿qué necesito para la partida de nacimiento?»';

    d.appendChild(icono); d.appendChild(p1); d.appendChild(p2);
    return d;
  }

  function fechaCorta(iso) {
    if (!iso) return '';
    var fecha = new Date(iso);
    if (isNaN(fecha.getTime())) return '';
    function dos(n) { return (n < 10 ? '0' : '') + n; }
    return dos(fecha.getDate()) + '/' + dos(fecha.getMonth() + 1) +
      ' ' + dos(fecha.getHours()) + ':' + dos(fecha.getMinutes());
  }

  function setConversacion(id) {
    var nuevo = id ? String(id) : '';
    if (nuevo !== conversacionActual) {
      guardarScroll();
      conversacionActual = nuevo;
      estadoChat.conversacion = nuevo;
      guardarEstadoChat();
      cargarBorrador();
    } else {
      estadoChat.conversacion = nuevo;
    }
  }

  function pintarConversaciones(lista, activa) {
    if (!listaChat) return;
    listaChat.innerHTML = '';

    if (!lista || !lista.length) {
      var vacio = document.createElement('p');
      vacio.className = 'chat-panel__vacio texto-chico texto-suave mb-0';
      vacio.textContent = 'Todavía no hay conversaciones.';
      listaChat.appendChild(vacio);
      return;
    }

    lista.forEach(function (c) {
      var boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'chat-panel__item' +
        (String(c.id) === String(activa) ? ' activo' : '');
      boton.setAttribute('data-conversacion', c.id);

      var nombre = document.createElement('span');
      nombre.className = 'chat-panel__nombre';
      nombre.textContent = c.titulo || 'Nueva conversación';

      var fecha = document.createElement('span');
      fecha.className = 'chat-panel__fecha';
      fecha.textContent = fechaCorta(c.actualizado);

      boton.appendChild(nombre);
      if (fecha.textContent) boton.appendChild(fecha);
      listaChat.appendChild(boton);
    });
  }

  function pintar(data, mantenerScroll) {
    if (!contChat) return;

    // Compatibilidad con la forma vieja (un array de mensajes).
    if (Array.isArray(data)) {
      data = { historial: data, conversacion: null, conversaciones: [] };
    }

    var historial = (data && data.historial) || [];
    if (data && data.conversacion) {
      setConversacion(data.conversacion.id);
    } else if (data && data.conversacion === null) {
      setConversacion('');
    }
    pintarConversaciones(
      (data && data.conversaciones) || [], conversacionActual
    );

    contChat.innerHTML = '';

    if (!historial.length) {
      contChat.appendChild(burbujaVacia());
    } else {
      historial.forEach(function (msg) {
        contChat.appendChild(
          burbuja(msg.texto || '', msg.rol, msg.segmentos)
        );
      });
    }

    chatCargado = true;
    if (mantenerScroll) restaurarScroll(); else bajar();
  }

  function cargarChat(conversacionId) {
    if (!window.MT.sesionIniciada) return Promise.resolve();
    var token = ++cargaChatToken;
    var url = window.MT.chatApi;
    if (conversacionId) {
      url += '?conversacion=' + encodeURIComponent(conversacionId);
    }
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (token === cargaChatToken) pintar(data, true);
      })
      .catch(function () { /* se queda con lo que ya estaba pintado */ });
  }

  function postChat(datos) {
    if (conversacionActual) {
      datos.append('conversacion', conversacionActual);
    }
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
    var claveEnvio = claveConversacion();

    // El campo se vacía apenas se manda: la pregunta ya se pinta en el
    // historial y no tiene que quedar escrita esperando la respuesta.
    entrada.value = '';
    delete estadoChat.borradores[claveEnvio];
    guardarEstadoChat();

    // Si se mandó desde la barra del listado, el modal tiene su propio
    // campo: también se vacía para que no quede la pregunta repetida.
    var entradaModal = document.querySelector(
      '#chat-form input[name=mensaje]'
    );
    if (entradaModal && entradaModal !== entrada) {
      entradaModal.value = '';
    }

    // Si el modal recién se abrió, la carga inicial puede llegar después
    // del POST y pisar la respuesta: este token la descarta.
    cargaChatToken += 1;
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
        pintar(data, false);
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
     chat, pero por /buscador/api/ y sin tocar la sesión).
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
          cuerpoBarra.appendChild(
            burbuja(data.texto || '', 'bot', data.segmentos)
          );
        })
        .catch(function () {
          cuerpoBarra.innerHTML = '';
          var aviso = document.createElement('p');
          aviso.className = 'mb-0';
          aviso.textContent = 'No pude consultar al asistente. ';
          var enlace = document.createElement('a');
          enlace.href = '#';
          enlace.setAttribute('data-abrir', 'modal-chat');
          enlace.setAttribute('data-chat-pregunta', consultaBarra);
          enlace.textContent = 'Intentar en el chat →';
          aviso.appendChild(enlace);
          cuerpoBarra.appendChild(aviso);
        });
    }
  }

  /* --------------------------------------------------------------------
     Barra lateral del modal: hamburguesa, lista de chats y «+ Nuevo»
     -------------------------------------------------------------------- */
  function panelAbierto() {
    return !!(panelChat &&
      panelChat.classList.contains('chat-panel--abierto'));
  }

  function abrirPanel() {
    if (!panelChat) return;
    panelChat.classList.add('chat-panel--abierto');
    panelChat.setAttribute('aria-hidden', 'false');
    if (fondoPanel) {
      fondoPanel.classList.add('chat-panel__fondo--abierto');
      fondoPanel.setAttribute('aria-hidden', 'false');
    }
    if (botonHamburguesa) {
      botonHamburguesa.setAttribute('aria-expanded', 'true');
    }
    estadoChat.panel = true;
    guardarEstadoChat();
    var primero = listaChat &&
      listaChat.querySelector('[data-conversacion]');
    if (primero) setTimeout(function () { primero.focus(); }, 30);
  }

  function cerrarPanel() {
    if (!panelChat) return;
    panelChat.classList.remove('chat-panel--abierto');
    panelChat.setAttribute('aria-hidden', 'true');
    if (fondoPanel) {
      fondoPanel.classList.remove('chat-panel__fondo--abierto');
      fondoPanel.setAttribute('aria-hidden', 'true');
    }
    if (botonHamburguesa) {
      botonHamburguesa.setAttribute('aria-expanded', 'false');
    }
    estadoChat.panel = false;
    guardarEstadoChat();
  }

  if (botonHamburguesa) {
    botonHamburguesa.addEventListener('click', function () {
      if (panelAbierto()) cerrarPanel(); else abrirPanel();
    });
  }

  if (listaChat) {
    listaChat.addEventListener('click', function (ev) {
      var boton = ev.target.closest('[data-conversacion]');
      if (!boton) return;
      var id = boton.getAttribute('data-conversacion');
      cerrarPanel();
      if (String(id) === String(conversacionActual)) return;
      cargarChat(id);
    });
  }

  if (entradaChat) {
    entradaChat.addEventListener('input', guardarBorrador);
  }

  if (contChat) {
    var temporizadorScroll = null;
    contChat.addEventListener('scroll', function () {
      clearTimeout(temporizadorScroll);
      temporizadorScroll = setTimeout(guardarScroll, 120);
    });
  }

  function crearNuevoChat(boton) {
    var datos = new FormData();
    datos.append('accion', 'nueva');
    boton.disabled = true;
    cargaChatToken += 1;
    postChat(datos)
      .then(function (data) {
        pintar(data, false);
        cerrarPanel();
        var campo = $('#chat-form input[name=mensaje]');
        if (campo) campo.focus();
      })
      .catch(function () { /* se queda como estaba */ })
      .then(function () { boton.disabled = false; });
  }

  var nuevoChat = document.getElementById('chat-nuevo');
  var nuevoChatPanel = document.getElementById('chat-nuevo-panel');
  [nuevoChat, nuevoChatPanel].forEach(function (boton) {
    if (!boton) return;
    boton.addEventListener('click', function () {
      crearNuevoChat(boton);
    });
  });

  // Recuperar el estado del modal antes de que el usuario lo abra.
  if (window.MT.sesionIniciada) {
    leerEstadoChat();
    limpiarEstadosChat(CLAVE_CHAT);
    conversacionActual = estadoChat.conversacion || '';
    cargarBorrador();
  } else {
    limpiarEstadosChat('');
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
    if (window.MT.sesionIniciada && estadoChat.abierto && !abierto) {
      abrir('modal-chat');
    }
  });
})();
