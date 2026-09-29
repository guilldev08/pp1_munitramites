"""ESP-01 / RF-01, RF-02, RF-14 y RF-15 — Autenticación.

Criterio de aceptación (documento): «El usuario puede registrarse, iniciar
sesión y cerrar sesión correctamente» y «restablecer su contraseña en caso
de olvido, mediante un mecanismo de verificación (ej. email)».
"""

from django.contrib.auth.models import User
from django.core import mail

from django.urls import reverse

from munitramites.models import Perfil

from .base import TestCase, administrador, ciudadano

REGISTRO = {
    'username': 'nuevo',
    'email': 'nuevo@munitramites.test',
    'first_name': 'Nuevo',
    'last_name': 'Ciudadano',
    'dni': '31222333',
    'password1': 'ClaveSegura123',
    'password2': 'ClaveSegura123',
}


class RegistroTests(TestCase):

    def test_registro_crea_cuenta_y_perfil_con_dni(self):
        """RF-01: registra, queda el usuario y su DNI (dato personal)."""
        r = self.client.post(reverse('registro'), REGISTRO)

        self.assertRedirects(r, reverse('login'))
        user = User.objects.get(username='nuevo')
        self.assertTrue(user.check_password('ClaveSegura123'))
        self.assertEqual(user.perfil.dni, '31222333')
        self.assertEqual(user.first_name, 'Nuevo')
        self.assertEqual(user.email, 'nuevo@munitramites.test')

    def test_el_modal_de_registro_se_abre_solo(self):
        """ESP-07: al llegar a /registro/ la pestaña Crear cuenta está activa."""
        r = self.client.get(reverse('registro'))

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].__class__.__name__ == 'RegistroForm')
        self.assertContains(r, 'modal--abierto')
        self.assertContains(r, 'Crear cuenta')

    def test_rechaza_dni_repetido(self):
        """Un DNI no puede pertenecer a dos cuentas."""
        ciudadano(username='primera', dni='30333444')
        datos = dict(REGISTRO, username='segunda', dni='30333444')

        r = self.client.post(reverse('registro'), datos)

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una cuenta con ese DNI')
        self.assertFalse(User.objects.filter(username='segunda').exists())

    def test_rechaza_correo_repetido(self):
        existente = ciudadano(username='primera')
        datos = dict(REGISTRO, username='segunda', email=existente.email)

        r = self.client.post(reverse('registro'), datos)

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una cuenta con ese correo')

    def test_rechaza_dni_invalido(self):
        datos = dict(REGISTRO, dni='abc')

        r = self.client.post(reverse('registro'), datos)

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '7 u 8 d')
        self.assertFalse(User.objects.filter(username='nuevo').exists())


class SesionTests(TestCase):

    def test_login_y_logout(self):
        """RF-02 y RF-14: entra con credenciales y cierra la sesión."""
        user = ciudadano(username='ana', password='ClaveSegura123')

        r = self.client.login(username='ana', password='ClaveSegura123')
        self.assertTrue(r)

        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

        r = self.client.post(reverse('logout'))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_con_clave_mala_no_entra(self):
        ciudadano(username='ana', password='ClaveSegura123')

        self.assertFalse(
            self.client.login(username='ana', password='otra-clave')
        )

    def test_la_pagina_de_login_es_la_del_sitio(self):
        r = self.client.get(reverse('login'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Munitramites')

    def test_sin_sesion_manda_al_login(self):
        """RF-13: sin sesión no se entra a las páginas privadas."""
        for url in (reverse('perfil'), reverse('consultas'),
                    reverse('soporte')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse('login'), r['Location'])


class RecuperarClaveTests(TestCase):
    """RF-15: restablecer la contraseña olvidada por email."""

    def test_pide_el_correo(self):
        r = self.client.get(reverse('password_reset'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'email')
        # Usa la plantilla del sitio, no la que trae django.contrib.admin
        self.assertContains(r, 'Recuperar contraseña')
        self.assertContains(r, 'Munitramites')

    def test_envia_el_enlace_y_permite_cambiar_la_clave(self):
        user = ciudadano(username='olvido', password='ClaveVieja123')

        r = self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertRedirects(r, reverse('password_reset_done'))

        # El correo sale por el backend de consola en producción y por el
        # buzón de memoria en los tests: los dos lo dejan ver aca.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)
        cuerpo = mail.outbox[0].body
        self.assertIn('/password/reset/', cuerpo)

        # Django tira el token en el cuerpo del mensaje
        url = [linea for linea in cuerpo.splitlines()
               if '/password/reset/' in linea][0].strip()

        # El primer GET redirige: Django guarda el token en la sesión y lo
        # saca de la URL para que no se filtre por el Referer.
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        url_formulario = r['Location']

        r = self.client.get(url_formulario)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'contraseña nueva')

        r = self.client.post(url_formulario, {
            'new_password1': 'ClaveNueva123',
            'new_password2': 'ClaveNueva123',
        })
        self.assertRedirects(r, reverse('password_reset_complete'))

        self.assertTrue(
            self.client.login(username='olvido', password='ClaveNueva123')
        )
        self.assertFalse(
            self.client.login(username='olvido', password='ClaveVieja123')
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password('ClaveNueva123'))

    def test_no_revela_si_el_correo_no_existe(self):
        r = self.client.post(reverse('password_reset'),
                             {'email': 'nadie@ejemplo.test'})
        self.assertRedirects(r, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)


class PerfilTests(TestCase):
    """«Consultar y modificar sus propios datos» (tipos de usuario)."""

    def test_muestra_los_datos(self):
        user = ciudadano(username='ana', dni='28111222')
        self.client.force_login(user)

        r = self.client.get(reverse('perfil'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '28111222')
        self.assertContains(r, 'ana@munitramites.test')

    def test_edita_nombre_apellido_correo_y_dni(self):
        user = ciudadano(username='ana', dni='28111222')
        self.client.force_login(user)

        r = self.client.post(reverse('perfil'), {
            'first_name': 'Maria',
            'last_name': 'Modificado',
            'email': 'ana@munitramites.test',
            'dni': '28999888',
        })

        self.assertRedirects(r, reverse('perfil'))
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Maria')
        self.assertEqual(user.last_name, 'Modificado')
        self.assertEqual(user.perfil.dni, '28999888')

    def test_no_puede_tomar_el_dni_de_otro(self):
        ciudadano(username='otra', dni='28777666')
        user = ciudadano(username='ana', dni='28111222')
        self.client.force_login(user)

        r = self.client.post(reverse('perfil'), {
            'first_name': 'Ana', 'last_name': 'Prueba',
            'email': 'ana@munitramites.test', 'dni': '28777666',
        })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una cuenta con ese DNI')
        user.perfil.refresh_from_db()
        self.assertEqual(user.perfil.dni, '28111222')

    def test_cambiar_clave_estando_adentro(self):
        user = ciudadano(username='ana')
        self.client.force_login(user)

        r = self.client.post(reverse('password_change'), {
            'old_password': 'ClaveSegura123',
            'new_password1': 'OtraClave1234',
            'new_password2': 'OtraClave1234',
        })

        self.assertRedirects(r, reverse('password_change_done'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('OtraClave1234'))
