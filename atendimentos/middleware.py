from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.get('force_password_change'):
            # URLs que o usuário pode acessar sem ser redirecionado (evita loop infinito)
            allowed_urls = [
                reverse('password_change'),
                reverse('password_change_done'),
                reverse('accounts:logout'),
            ]

            if request.path not in allowed_urls and not request.path.startswith('/static/'):
                messages.warning(request, "Você deve alterar sua senha inicial antes de prosseguir.")
                return redirect('password_change')

        return self.get_response(request)