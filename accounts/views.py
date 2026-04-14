from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
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
    next_page = reverse_lazy("accounts:login")
    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        # Django 5+ removeu GET do LogoutView; redireciona para login sem deslogar.
        return redirect("accounts:login")


class RegisterUserView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterUserForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, "403.html", status=403)
        if getattr(request.user, "perfil", None) != "admin":
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        # Redireciona para monitores quando perfil=monitor, para facilitar o vínculo com turma.
        if user.perfil == "monitor":
            return redirect("curriculum:monitores_list")
        return redirect("curriculum:disciplinas_list")

