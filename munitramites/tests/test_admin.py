"""Panel de administración: la cara (ESP-02) y el candado (RF-13).

Dos puertas, dos reglas:

* **`/admin/` de Django** — EXCLUSIVO del superusuario. Cualquier
  administrador que lo pise queda redirigido a `/panel/` con un aviso
  claro (`middleware.AdminSoloSuperusuario`).
* **`/panel/`** — el panel propio, donde el rol Administrador vive el
  día a día (ver `test_panel.py`).

Y la regla de oro: **UNA sola cuenta de superusuario**, impuesta por
código en `senales.py` — ni la admin ni la shell crean un segundo.
"""

from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse

from munitramites.models import Consulta, Organismo, Tramite

from .base import TestCase, administrador, ciudadano, superusuario, tramite


class VistaDelPanelTests(TestCase):
    """La parte «amigable»: el panel no tiene que verse pelado."""

    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def test_la_marca_aparece_en_la_barra_y_en_el_titulo(self):
        r = self.client.get(reverse('admin:index'))

        self.assertContains(r, 'Munitramites · Panel de administración')
        self.assertContains(r, 'Resumen general')

    def test_el_indice_muestra_saludo_tarjetas_y_atajos(self):
        r = self.client.get(reverse('admin:index'))

        for texto in ('admin-saludo', 'panel-resumen', 'Trámites activos',
                      'Consultas sin responder', 'Atajos',
                      'Ver el sitio público', 'Cambiar mi contraseña'):
            self.assertContains(r, texto)

    def test_las_tarjetas_cuentan_lo_que_hay(self):
        tramite()
        tramite(titulo='Pasaporte argentino')
        Consulta.objects.create(asunto='Horarios', contenido='¿Abren de noche?')

        r = self.client.get(reverse('admin:index'))

        self.assertContains(r, 'de 2 cargados')
        self.assertContains(r, 'de 1 recibidas')

    def test_los_enlaces_de_las_tarjetas_llevan_al_listado_filtrado(self):
        r = self.client.get(reverse('admin:index'))

        self.assertContains(r, '/admin/munitramites/tramite/?activo__exact=1')
        self.assertContains(
            r, '/admin/munitramites/consulta/?estado__exact=pendiente'
        )

    def test_el_login_tambien_lleva_la_marca(self):
        self.client.logout()

        r = self.client.get(reverse('admin:login'))

        self.assertContains(r, 'Munitramites · Panel de administración')

    def test_las_columnas_se_pintan_con_pildoras(self):
        tramite()  # tema Documentación (azul)
        Consulta.objects.create(asunto='Ruido en la calle', contenido='...')

        r = self.client.get(reverse('admin:munitramites_tramite_changelist'))
        self.assertContains(r, 'pildora--azul')

        r = self.client.get(reverse('admin:munitramites_consulta_changelist'))
        self.assertContains(r, 'pildora--ambar')  # pendiente
        self.assertContains(r, 'Pendiente')

    def test_hay_acciones_para_publicar_y_para_responder(self):
        # Django solo pinta la barra de acciones si hay filas en el listado.
        tramite()
        Consulta.objects.create(asunto='Turnos', contenido='¿Abren?')

        r = self.client.get(reverse('admin:munitramites_tramite_changelist'))
        self.assertContains(r, 'Activar los trámites seleccionados')
        self.assertContains(r, 'Desactivar los trámites seleccionados')

        r = self.client.get(reverse('admin:munitramites_consulta_changelist'))
        self.assertContains(r, 'Marcar como respondidas')
        self.assertContains(r, 'Cerrar las consultas seleccionadas')

    def test_las_acciones_masivas_de_verdad_publican(self):
        t = tramite(activo=False)

        r = self.client.post(reverse('admin:munitramites_tramite_changelist'), {
            'action': 'activar',
            'index': '0',
            '_selected_action': [str(t.pk)],
        })

        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertTrue(t.activo)

    def test_solo_el_superusuario_ve_la_accion_de_borrar(self):
        tramite()  # sin filas Django no pinta la barra de acciones

        r = self.client.get(reverse('admin:munitramites_tramite_changelist'))
        self.assertContains(r, 'delete_selected')


class EditorRedirigidoTests(TestCase):
    """Rol Administrador: /admin/ no es su puerta — lo manda a /panel/."""

    def setUp(self):
        self.editor = administrador()
        self.client.force_login(self.editor)

    def test_toda_url_del_admin_lo_manda_al_panel(self):
        for url in (reverse('admin:index'),
                    reverse('admin:munitramites_tramite_changelist'),
                    reverse('admin:munitramites_consulta_changelist'),
                    reverse('admin:auth_user_changelist'),
                    reverse('admin:auth_group_changelist'),
                    reverse('admin:munitramites_perfil_changelist')):
            r = self.client.get(url)

            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r['Location'], reverse('panel'), url)

    def test_los_post_tambien_quedan_afuera(self):
        """Ni un borrado ni una edición llegan a escribir en la base."""
        t = tramite()

        r = self.client.post(
            reverse('admin:munitramites_tramite_delete', args=[t.pk])
        )

        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('panel'))
        self.assertTrue(Tramite.objects.filter(pk=t.pk).exists())

    def test_el_aviso_le_dice_por_que_no_pasa(self):
        r = self.client.get(reverse('admin:index'), follow=True)

        self.assertContains(r, 'solo para el superusuario')
        # Termina en el panel, con sus dos centros a la vista
        self.assertContains(r, 'Centro de Trámites')
        self.assertContains(r, 'Centro de Consultas')

    def test_el_editor_no_es_superusuario(self):
        self.assertTrue(self.editor.is_staff)
        self.assertFalse(self.editor.is_superuser)

    def test_en_el_panel_si_puede_gestionar(self):
        for url in (reverse('panel'), reverse('panel_tramites'),
                    reverse('panel_consultas'), reverse('panel_usuarios')):
            self.assertEqual(self.client.get(url).status_code, 200, url)


class FilaPropiaTests(TestCase):
    """Nadie se edita ni se borra a sí mismo (en /admin/, con superusuario)."""

    def setUp(self):
        self.jefe = superusuario(username='jefe')
        self.client.force_login(self.jefe)
        self.registro = site._registry[User]

    def test_en_el_api_los_permisos_se_aclaran_por_fila(self):
        otro = ciudadano(username='otro')
        pedido = RequestFactory().get('/')
        pedido.user = self.jefe

        self.assertFalse(
            self.registro.has_change_permission(pedido, self.jefe)
        )
        self.assertFalse(
            self.registro.has_delete_permission(pedido, self.jefe)
        )
        self.assertTrue(self.registro.has_change_permission(pedido, otro))
        self.assertTrue(self.registro.has_delete_permission(pedido, otro))

    def test_su_fila_se_abre_en_solo_lectura(self):
        r = self.client.get(
            reverse('admin:auth_user_change', args=[self.jefe.pk])
        )

        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['has_change_permission'])

    def test_no_puede_guardar_cambios_en_su_propia_fila(self):
        r = self.client.post(
            reverse('admin:auth_user_change', args=[self.jefe.pk]),
            {'username': 'jefe', 'email': 'hackeadito@x.test'},
        )

        self.assertEqual(r.status_code, 403)
        self.jefe.refresh_from_db()
        self.assertEqual(self.jefe.email, 'jefe@munitramites.test')

    def test_no_puede_borrarse_a_si_mismo(self):
        r = self.client.get(
            reverse('admin:auth_user_delete', args=[self.jefe.pk])
        )

        self.assertEqual(r.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.jefe.pk).exists())


class RegistroDeConsultasTests(TestCase):
    """`usuario` y `fecha` son registro: no se editan desde el panel."""

    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def test_en_la_ficha_existente_son_de_solo_lectura(self):
        autor = ciudadano(username='ana')
        consulta = Consulta.objects.create(
            asunto='Horarios', contenido='¿Abren?', usuario=autor,
        )

        r = self.client.get(
            reverse('admin:munitramites_consulta_change', args=[consulta.pk])
        )

        self.assertEqual(r.status_code, 200)
        self.assertIn('usuario', r.context['adminform'].readonly_fields)
        self.assertIn('fecha', r.context['adminform'].readonly_fields)

    def test_al_crearla_si_se_puede_decir_de_quien_es(self):
        r = self.client.get(reverse('admin:munitramites_consulta_add'))

        self.assertEqual(r.status_code, 200)
        self.assertNotIn('usuario', r.context['adminform'].readonly_fields)


class SuperusuarioTests(TestCase):
    """Al superusuario no se le cierra ninguna puerta."""

    def setUp(self):
        self.admin = superusuario()
        self.client.force_login(self.admin)

    def test_ve_las_cuentas_los_grupos_y_los_perfiles(self):
        for url in (reverse('admin:auth_user_changelist'),
                    reverse('admin:auth_group_changelist'),
                    reverse('admin:munitramites_perfil_changelist')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)

    def test_si_puede_borrar_a_otros(self):
        otro = ciudadano(username='otro')

        r = self.client.get(
            reverse('admin:auth_user_delete', args=[otro.pk])
        )

        self.assertEqual(r.status_code, 200)

    def test_puede_cargar_un_organismo_con_su_area_de_accion(self):
        """RF-05: organismos y municipios son territorio de /admin/."""
        r = self.client.post(reverse('admin:munitramites_organismo_add'), {
            'nombre': 'Direccion de Catastro',
            'direccion': 'Calle San Martin 321',
            'ocupacion': 'Bienes raices',
        })

        self.assertEqual(r.status_code, 302)
        self.assertTrue(Organismo.objects.filter(
            nombre='Direccion de Catastro', ocupacion='Bienes raices'
        ).exists())


class CapturaDeMensajes:
    """Almacenamiento mínimo de mensajes: solo para el test de abajo.

    Hace el mismo trabajo que hace MessageMiddleware en la vida real
    (`request._messages.add(...)`), sin arrastrar sesiones ni cookies.
    """

    def __init__(self):
        self.guardados = []

    def add(self, nivel, mensaje, extra_tags=''):
        self.guardados.append((nivel, mensaje))


class UnSoloSuperusuarioTests(TestCase):
    """La regla de oro, impuesta por `senales.py` en el pre_save de User."""

    def setUp(self):
        self.jefe = superusuario()

    def test_no_se_puede_crear_un_segundo_superusuario(self):
        with self.assertRaises(ValidationError) as ctx:
            User.objects.create_superuser(
                username='otro', email='otro@munitramites.test',
                password='ClaveSegura123',
            )

        self.assertIn('UN superusuario', str(ctx.exception))

    def test_tampoco_se_puede_elevar_a_un_ciudadano(self):
        ana = ciudadano(username='ana')
        ana.is_superuser = True

        with self.assertRaises(ValidationError):
            ana.save()

        ana.refresh_from_db()
        self.assertFalse(ana.is_superuser)

    def test_el_guard_no_toca_a_las_demas_cuentas(self):
        """Ciudadanos y administradores se crean (y se editan) sin drama."""
        ciudadano(username='ana')
        administrador(username='staff')

        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_en_el_admin_no_explota_sino_que_avisa(self):
        """UserAdmin.save_model atrapa la regla: ni 500 ni segundo super."""
        objetivo = ciudadano(username='ana')
        objetivo.is_superuser = True  # alguien lo intentó desde el form

        pedido = RequestFactory().post('/admin/auth/user/%d/change/' % objetivo.pk)
        pedido.user = self.jefe
        pedido._messages = CapturaDeMensajes()

        site._registry[User].save_model(pedido, objetivo, form=None, change=True)

        objetivo.refresh_from_db()
        self.assertFalse(objetivo.is_superuser)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)
        # El form quedó con el aviso, no con un error 500
        self.assertTrue(pedido._messages.guardados)
