from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def verificar_troca_senha_obrigatoria(sender, request, user, **kwargs):
    """
    Ao logar, verifica se o usuário é monitor e se possui a flag 'deve_trocar_senha'.
    Se sim, marca a sessão para que o middleware intercepte as próximas requisições.
    """
    if user.perfil == 'monitor' and getattr(user, 'deve_trocar_senha', False):
        request.session['force_password_change'] = True