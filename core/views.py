from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    perfil = getattr(request.user, "perfil", None)
    if perfil == "monitor":
        return redirect("atendimentos:lista_meus_atendimentos")
    if perfil == "professor":
        return redirect("relatorios:dashboard_professor")
    if perfil == "admin":
        return redirect("curriculum:disciplinas_list")
    return redirect("accounts:login")


@login_required
def perfil(request):
    """
    Página simples para exibir o perfil do usuário logado.
    """
    return render(request, "core/perfil.html", {"perfil": request.user.perfil})

