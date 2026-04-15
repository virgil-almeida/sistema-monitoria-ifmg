from functools import wraps

from django.conf import settings
from django.shortcuts import redirect, render


def perfil_requerido(perfil: str):
    """
    Decorator simples para restringir uma view a um perfil específico.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if getattr(request.user, "perfil", None) != perfil:
                return render(
                    request,
                    "403.html",
                    {"exception": f"Esta página exige perfil '{perfil}'. Seu perfil atual é '{request.user.perfil or 'nenhum'}'."},
                    status=403,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator

