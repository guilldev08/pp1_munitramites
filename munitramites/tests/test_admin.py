"""Panel de administración: la cara (ESP-02) y el candado (RF-13).

El panel tiene que verse como un producto propio —marca, tarjetas de resumen,
píldoras de color, atajos y acciones— y al mismo tiempo cerrar el paso según
el rol:

* **Superusuario**: todo (usuarios, grupos, perfiles y borrado).
* **Editor** (`is_staff`, sin superusuario): contenido del sitio, sin cuentas
  y sin borrado.
* **Nadie**: su propia fila de usuario (para no quedar afuera del sistema).
"""

from django.contrib.admin.sites import site
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory
from django.urls import reverse

from munitramites.models import Consulta

from .base import TestCase, administrador, ciudadano, tramite


def editor(username='editor'):
    """Rol intermedio: entra al panel y gestiona el contenido, nada más.

    Tiene TODOS los permisos de la app `munitramites` (incluido «borrar») para
    que los tests prueben el candado del panel y no la ausencia de permisos.
    """
    user = User.objects.create_user(
        username=username, password='ClaveSegura123', is_staff=True,
    )
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label='munitramites')
    )
    return user


class VistaDelPanelTests(TestCase):
    """La parte «amigable»: el panel no tiene que verse pelado."""

    def setUp(self):
        self.admin = administrador()
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


class CandadoDelEditorTests(TestCase):
    """Rol Editor: entra al contenido, no toca cuentas ni borra."""

    def setUp(self):
        self.editor = editor()
        self.client.force_login(self.editor)

    def test_entra_al_panel_y_ve_el_contenido(self):
        r = self.client.get(reverse('admin:index'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '/admin/munitramites/tramite/')
        self.assertContains(r, 'panel-resumen')

    def test_los_modulos_sensibles_le_dan_403(self):
        for url in (reverse('admin:auth_user_changelist'),
                    reverse('admin:auth_group_changelist'),
                    reverse('admin:munitramites_perfil_changelist')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403, url)

    def test_los_modulos_sensibles_ni_se_le_listan(self):
        r = self.client.get(reverse('admin:index'))

        for no_ver in ('/admin/auth/user/', '/admin/auth/group/',
                       '/admin/munitramites/perfil/'):
            self.assertNotContains(r, no_ver)

    def test_no_puede_borrar_ni_tramites_ni_consultas(self):
        t = tramite()
        c = Consulta.objects.create(asunto='Horarios', contenido='¿Abren?')

        for url in (reverse('admin:munitramites_tramite_delete', args=[t.pk]),
                    reverse('admin:munitramites_consulta_delete', args=[c.pk])):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403, url)

    def test_no_le_aparece_la_accion_de_borrar(self):
        tramite()  # sin filas Django no pinta la barra de acciones

        r = self.client.get(reverse('admin:munitramites_tramite_changelist'))

        self.assertNotContains(r, 'delete_selected')

    def test_si_puede_dar_de_alta_y_editar_contenido(self):
        self.assertEqual(
            self.client.get(reverse('admin:munitramites_tramite_add')).status_code,
            200,
        )

        t = tramite()
        r = self.client.get(
            reverse('admin:munitramites_tramite_change', args=[t.pk])
        )
        self.assertEqual(r.status_code, 200)

    def test_si_puede_responder_consultas(self):
        c = Consulta.objects.create(asunto='Turnos', contenido='¿Hay turno?')

        r = self.client.get(
            reverse('admin:munitramites_consulta_change', args=[c.pk])
        )

        self.assertEqual(r.status_code, 200)

    def test_el_fixture_no_es_superusuario(self):
        self.assertFalse(self.editor.is_superuser)


class FilaPropiaTests(TestCase):
    """Nadie se edita ni se borra a sí mismo."""

    def setUp(self):
        self.jefe = administrador(username='jefe')
        self.client.force_login(self.jefe)
        self.registro = site._registry[User]

    def test_en_el_api_los_permisos_se_aclaran_por_fila(self):
        otro = administrador(username='otro')
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
        self.admin = administrador()
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
        self.admin = administrador()
        self.client.force_login(self.admin)

    def test_ve_las_cuentas_los_grupos_y_los_perfiles(self):
        for url in (reverse('admin:auth_user_changelist'),
                    reverse('admin:auth_group_changelist'),
                    reverse('admin:munitramites_perfil_changelist')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)

    def test_si_puede_borrar_a_otros(self):
        otro = administrador(username='otro')

        r = self.client.get(
            reverse('admin:auth_user_delete', args=[otro.pk])
        )

        self.assertEqual(r.status_code, 200)
