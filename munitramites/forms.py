"""
Formularios. >>> ACÁ SE VALIDAN LOS DATOS <<<

Django valida en el servidor. Si el usuario escribe cualquier cosa, el
formulario vuelve con errores y NO llega a la base.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Consulta, Municipio, Perfil, Tema, Tramite


class RegistroForm(UserCreationForm):
    """Alta de ciudadano. Hereda toda la validacion de Django.

    Además de los campos de `User` pide el DNI (dato personal que exige el
    documento) y lo guarda en `Perfil` al crear la cuenta.
    """

    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'nombre@correo.com',
            'autocomplete': 'email',
        }),
    )
    dni = forms.CharField(
        label='DNI',
        max_length=12,
        widget=forms.TextInput(attrs={
            'placeholder': 'Sin puntos, ej.: 12345678',
            'inputmode': 'numeric',
            'autocomplete': 'off',
        }),
        help_text='Entre 7 y 8 dígitos, sin puntos.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'username': 'Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'tu_usuario'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Apellido'}),
        }

    def clean_dni(self):
        return validar_dni(self.cleaned_data['dni'])

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            # La cuenta y su perfil se crean juntas
            Perfil.objects.create(user=user, dni=self.cleaned_data['dni'])
        return user


def validar_dni(valor):
    """7 u 8 dígitos, sin puntos, y que no esté ya registrado."""
    dni = valor.replace('.', '').replace(' ', '').strip()
    if not dni.isdigit() or not 7 <= len(dni) <= 8:
        raise forms.ValidationError('El DNI debe tener 7 u 8 dígitos, sin puntos.')
    if Perfil.objects.filter(dni=dni).exists():
        raise forms.ValidationError('Ya existe una cuenta con ese DNI.')
    return dni


class PerfilForm(forms.ModelForm):
    """Edición de los datos personales: nombre, apellido, correo y DNI."""

    dni = forms.CharField(
        label='DNI',
        max_length=12,
        widget=forms.TextInput(attrs={
            'placeholder': 'Sin puntos, ej.: 12345678',
            'inputmode': 'numeric',
        }),
        help_text='Entre 7 y 8 dígitos, sin puntos.',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
        }

    def clean_dni(self):
        dni = validar_dni(self.cleaned_data['dni'])
        # El DNI propio no cuenta como repetido
        if self.instance and self.instance.pk:
            if Perfil.objects.filter(dni=dni).exclude(
                user__pk=self.instance.pk
            ).exists():
                raise forms.ValidationError('Ya existe una cuenta con ese DNI.')
        return dni

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
            'placeholder': 'Buscar trámite o requisito…',
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

        if datos['q']:
            queryset = queryset.filter(
                Q(titulo__icontains=datos['q'])
                | Q(descripcion__icontains=datos['q'])
                | Q(requisitos__descripcion__icontains=datos['q'])
            ).distinct()
        if datos['tema']:
            queryset = queryset.filter(tema_id=datos['tema'])
        if datos['municipio']:
            queryset = queryset.filter(municipio_id=datos['municipio'])
        if datos['modalidad']:
            queryset = queryset.filter(modalidad=datos['modalidad'])
        return queryset
