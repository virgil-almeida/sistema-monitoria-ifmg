from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from core.permissions import perfil_requerido

from accounts.forms import RegisterUserForm


class MyLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        perfil = getattr(self.request.user, "perfil", None)
        if perfil == "monitor":
            return reverse("atendimentos:lista_meus_atendimentos")
        if perfil == "professor":
            return reverse("relatorios:dashboard_professor")
        if perfil == "admin":
            return reverse("curriculum:disciplinas_list")
        return super().get_success_url()


class MyLogoutView(LogoutView):
    def get_next_page(self):
        return reverse("accounts:login")


@perfil_requerido("admin")
class RegisterUserView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterUserForm

    def form_valid(self, form):
        user = form.save()
        # Não logamos automaticamente: admin deve criar e navegar.
        return redirect("curriculum:disciplinas_list")

