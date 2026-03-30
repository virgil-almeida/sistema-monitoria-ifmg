from functools import wraps

from django.shortcuts import render


def perfil_requerido(perfil: str):
    """
    Decorator simples para restringir uma view a um perfil específico.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "403.html", status=403)
            if getattr(request.user, "perfil", None) != perfil:
                return render(request, "403.html", status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator

