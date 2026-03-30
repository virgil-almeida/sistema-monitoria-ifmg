from django.shortcuts import render


class PerfilAtivoMiddleware:
    """
    Garante que o usuário autenticado possua um perfil válido no sistema.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            perfil = getattr(user, "perfil", None)
            if not perfil:
                return render(request, "403.html", status=403)
        return self.get_response(request)

