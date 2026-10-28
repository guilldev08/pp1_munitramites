"""
Formularios. >>> ACÁ SE VALIDAN LOS DATOS <<<

Django valida en el servidor. Si el usuario escribe cualquier cosa, el
formulario vuelve con errores y NO llega a la base.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import inlineformset_factory

from .models import (
    ArchivoTramite, Consulta, Direccion, Enlace, Municipio, Perfil,
    Requisito, Tema, Tramite,
)
from .services.busqueda import buscar_tramites


class RegistroForm(UserCreationForm):
    """Alta de ciudadano. Hereda toda la validacion de Django.

    Los datos de la cuenta son los mínimos: usuario, correo y contraseña.
    El sitio no pide documentos ni nombres —para eso no hace falta ser
    una página random de trámites.
    """

    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'nombre@correo.com',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'tu_usuario'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            # La cuenta y su perfil (que solo guarda el rol) se crean juntas
            Perfil.objects.create(user=user)
        return user


class PerfilForm(forms.ModelForm):
    """Edición del correo de la cuenta.

    El usuario y la contraseña no se tocan desde acá: el primero es el
    identificador y la clave tiene su propio flujo («Cambiar mi
    contraseña» y el RF-15 de recuperación).
    """

    class Meta:
        model = User
        fields = ['email']
        labels = {
            'email': 'Correo electrónico',
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email


class ConsultaForm(forms.ModelForm):
    """Consulta o sugerencia que envia un ciudadano."""

    class Meta:
        model = Consulta
        fields = ['tipo', 'tramite', 'asunto', 'contenido']
        widgets = {
            'tramite': forms.Select(attrs={'class': 'select'}),
            'asunto': forms.TextInput(attrs={
                'placeholder': 'Ej: Horarios de atención del Registro Civil',
                'maxlength': 200,
            }),
            'contenido': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Escribí tu consulta con el mayor detalle posible…',
                'minlength': 10,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El combo de tramite es opcional y arranca con un placeholder
        self.fields['tramite'].required = False
        self.fields['tramite'].empty_label = '— Sin trámite asociado —'


class SoporteForm(forms.Form):
    """Reporte de un problema del sitio. Solo lo puede enviar un usuario
    logueado (la vista aplica @login_required) y se guarda como consulta
    con el asunto inicializado en «Soporte: », asi aparece en el admin y
    en «Mis consultas» sin tocar el esquema de la base.
    """

    asunto = forms.CharField(
        label='Asunto',
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej: No puedo abrir la ficha de un trámite',
            'maxlength': 200,
            'autocomplete': 'off',
        }),
    )
    mensaje = forms.CharField(
        label='Describe el problema',
        min_length=10,
        max_length=4000,
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Qué hiciste, qué esperabas y qué pasó. '
                           'Cuantos más detalles, mejor.',
            'minlength': 10,
        }),
    )


class TramiteFiltroForm(forms.Form):
    """Filtros de la lista de tramites (se leen del querystring)."""

    q = forms.CharField(
        required=False,
        label='Buscar',
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar trámite, requisito o dirección…',
            'type': 'search',
        }),
    )
    tema = forms.ChoiceField(
        required=False, choices=[('', 'Todos los temas')]
    )
    municipio = forms.ChoiceField(
        required=False, choices=[('', 'Todos los municipios')]
    )
    modalidad = forms.ChoiceField(
        required=False, choices=[('', 'Todas las modalidades')]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tema'].choices += [(t.pk, t.nombre)
                                        for t in Tema.objects.all()]
        self.fields['municipio'].choices += [
            (m.pk, m.nombre) for m in Municipio.objects.all()
        ]
        self.fields['modalidad'].choices += list(Tramite.Modalidad.choices)

    def filtrar(self, queryset):
        """Aplica los filtros validados al queryset de tramites."""
        if not self.is_valid():
            return queryset
        datos = self.cleaned_data

        if datos['tema']:
            queryset = queryset.filter(tema_id=datos['tema'])
        if datos['municipio']:
            # El municipio principal del trámite o cualquiera de sus sedes:
            # así un trámite compartido aparece al filtrar por Oberá aunque
            # su municipio principal sea Posadas.
            queryset = queryset.filter(
                Q(municipio_id=datos['municipio'])
                | Q(direcciones__municipio_id=datos['municipio'])
            ).distinct()
        if datos['modalidad']:
            queryset = queryset.filter(modalidad=datos['modalidad'])

        # La búsqueda flexible va al final: ordena por relevancia. Tolera
        # tildes, mayúsculas, plurales, palabras parciales y sinónimos.
        if datos['q']:
            queryset = buscar_tramites(queryset, datos['q'])
        return queryset


# =============================================================================
# Panel de administración (/panel/) — Centro de Trámites, Centro de Consultas,
# gestión de usuarios y temas. Mismo estilo de validación que el resto:
# >>> ACÁ SE VALIDAN LOS DATOS <<< y nada llega a la base si no cierran.
# =============================================================================


class TemaForm(forms.ModelForm):
    """Alta de temas desde el panel (RF-07): sin tocar código."""

    class Meta:
        model = Tema
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej.: Medio Ambiente',
                'autocomplete': 'off',
            }),
        }


class TramitePanelForm(forms.ModelForm):
    """Alta y edición de trámites desde el Centro de Trámites.

    Los requisitos, los enlaces y las direcciones no viajan en este form:
    se cargan con los formsets de acá abajo (`RequisitoFormSet`,
    `EnlaceFormSet` y `DireccionFormSet`), que se validan y se guardan
    juntos con el trámite. No hay campos fijos para «turnos» ni «sitio
    oficial»: cada botón se carga con el nombre que se le quiera dar y su
    URL. `municipio` es el municipio principal; las sedes adicionales van
    en Direcciones.
    """

    class Meta:
        model = Tramite
        fields = [
            'titulo', 'tema', 'modalidad', 'municipio', 'organismo',
            'descripcion', 'destacado', 'activo',
        ]
        labels = {'municipio': 'Municipio principal'}
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ej.: Renovación del DNI',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Qué se hace, dónde, cuándo y a quién acudir…',
            }),
        }


# Inlines del Centro de Trámites: el usuario NO escribe el «orden». Lo
# numera el panel solo, por la posición de la fila visible (ver
# views/panel.py), así no hay ningún campo obligatorio escondido que
# trabe el guardado. `extra=3` deja tres filas vacías listas; para seguir
# cargando hay un botón «+ Agregar» que clona una fila nueva, y la fila
# marcada «Eliminar» sale de la lista (app.js, prepararInlines()).
class RequisitoInlineForm(forms.ModelForm):
    """Fila de requisito: la descripción se numera sola por su posición."""

    class Meta:
        model = Requisito
        fields = ['descripcion']
        labels = {'descripcion': 'Descripción'}
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Ej.: DNI vigente y formulario completo',
            }),
        }


class EnlaceInlineForm(forms.ModelForm):
    """Fila de enlace: el nombre que se ve en el botón y la URL."""

    class Meta:
        model = Enlace
        fields = ['nombre', 'url']
        labels = {
            'nombre': 'Nombre del botón',
            'url': 'URL',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej.: Pedir turno',
            }),
            'url': forms.URLInput(attrs={'placeholder': 'https://…'}),
        }


RequisitoFormSet = inlineformset_factory(
    Tramite, Requisito,
    form=RequisitoInlineForm,
    fields=['descripcion'],
    extra=3,
    can_delete=True,
)

class DireccionInlineForm(forms.ModelForm):
    """Fila de dirección: sede, municipio y dirección física."""

    class Meta:
        model = Direccion
        fields = ['lugar', 'municipio', 'direccion']
        labels = {
            'lugar': 'Lugar',
            'municipio': 'Municipio',
            'direccion': 'Dirección',
        }
        widgets = {
            'lugar': forms.TextInput(attrs={
                'placeholder': 'Ej.: Registro Civil Centro',
            }),
            'direccion': forms.TextInput(attrs={
                'placeholder': 'Ej.: Av. Mitre 1234, Posadas',
            }),
        }


EnlaceFormSet = inlineformset_factory(
    Tramite, Enlace,
    form=EnlaceInlineForm,
    fields=['nombre', 'url'],
    extra=3,
    can_delete=True,
)

DireccionFormSet = inlineformset_factory(
    Tramite, Direccion,
    form=DireccionInlineForm,
    fields=['lugar', 'municipio', 'direccion'],
    extra=2,
    can_delete=True,
)


class ArchivoInlineForm(forms.ModelForm):
    """Fila de archivo descargable: formulario, instructivo o documento."""

    class Meta:
        model = ArchivoTramite
        fields = ['titulo', 'tipo', 'archivo', 'descripcion']
        labels = {
            'titulo': 'Título',
            'tipo': 'Tipo',
            'archivo': 'Archivo',
            'descripcion': 'Descripción',
        }
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ej.: Formulario de solicitud',
            }),
            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Para qué sirve o cómo se completa (opcional)',
            }),
        }
        help_texts = {
            'archivo': 'PDF, Word o imagen. Se descarga desde la ficha pública.',
        }


ArchivoFormSet = inlineformset_factory(
    Tramite, ArchivoTramite,
    form=ArchivoInlineForm,
    fields=['titulo', 'tipo', 'archivo', 'descripcion'],
    extra=2,
    can_delete=True,
)


class RespuestaConsultaForm(forms.Form):
    """Respuesta que el administrador le da a una consulta (RF-10)."""

    respuesta = forms.CharField(
        label='Respuesta',
        min_length=5,
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Escribí la respuesta para el ciudadano…',
            'minlength': 5,
        }),
        help_text='Mínimo 5 caracteres. El ciudadano la ve en «Mis consultas».',
    )


class UsuarioPanelForm(UserCreationForm):
    """Alta de cuentas desde el panel con cualquiera de los tres roles.

    Los datos son los mismos que en el registro —usuario, correo y
    contraseña—, más el rol. Tiene un campo `rol` propio (nunca
    `is_superuser`): desde el panel NO se puede crear un superusuario —
    esa cuenta única se hace con `manage.py createsuperuser` y la regla
    la vigila `senales.py`.
    """

    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'nombre@correo.com',
            'autocomplete': 'email',
        }),
    )
    rol = forms.ChoiceField(
        label='Rol',
        choices=[
            ('corriente', 'Usuario corriente'),
            ('administrativo', 'Usuario administrativo'),
            ('administrador', 'Usuario administrador'),
        ],
        initial='corriente',
        help_text='Los roles se acumulan: «Administrativo» gestiona '
                  'trámites, consultas y temas; «Administrador» además '
                  'gestiona las cuentas; «Corriente» solo usa el sitio.',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'tu_usuario'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email

    def save(self, commit=True):
        # `is_superuser` ni aparece en el form: queda en False siempre.
        user = super().save(commit)
        rol = self.cleaned_data['rol']
        user.is_staff = rol != Perfil.Rol.CORRIENTE
        if commit:
            user.save()
            Perfil.objects.create(user=user, rol=rol)
        return user


class UsuarioRolForm(forms.ModelForm):
    """Edición de una cuenta ajena desde el panel: datos, rol y actividad.

    Es un `ModelForm` sobre `User` pero SIN `is_superuser` en `fields`:
    el panel puede mover una cuenta entre los tres roles (gestión de
    roles), pero nunca elevarla a superusuario. El rol viaja en un campo
    propio, se guarda en `Perfil.rol` y deja `is_staff` sincronizado.
    """

    rol = forms.ChoiceField(
        label='Rol',
        choices=[
            ('corriente', 'Usuario corriente'),
            ('administrativo', 'Usuario administrativo'),
            ('administrador', 'Usuario administrador'),
        ],
        help_text='Los roles se acumulan: «Administrativo» gestiona '
                  'trámites, consultas y temas; «Administrador» además '
                  'gestiona las cuentas; «Corriente» solo usa el sitio.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'is_active']
        labels = {
            'username': 'Usuario',
            'is_active': 'Cuenta activa',
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'tu_usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El combo arranca con el rol actual de la cuenta. El perfil puede
        # no existir en cuentas viejas: ahí se mira is_staff (que es el
        # espejo del rol) y no se pierde la edición.
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil is not None:
                self.fields['rol'].initial = perfil.rol
            else:
                self.fields['rol'].initial = (
                    'administrativo' if self.instance.is_staff else 'corriente'
                )
        self.fields['is_active'].help_text = (
            'Sin marca: la cuenta queda suspendida y no puede ingresar.'
        )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        rol = self.cleaned_data['rol']
        user.is_staff = rol != Perfil.Rol.CORRIENTE
        if commit:
            user.save()
            perfil, _ = Perfil.objects.get_or_create(user=user)
            perfil.rol = rol
            perfil.save()
        return user
