from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import Usuario


class RegisterUserForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "perfil", "password1", "password2")

    perfil = forms.ChoiceField(choices=Usuario.PERFIL_CHOICES)

