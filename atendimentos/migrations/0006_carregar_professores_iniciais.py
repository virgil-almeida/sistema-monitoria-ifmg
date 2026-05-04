import json
import os
from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password

def carregar_professores(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    fixture_path = os.path.join(settings.BASE_DIR, 'atendimentos', 'fixtures', 'professores_iniciais.json')
    
    if not os.path.exists(fixture_path):
        return

    with open(fixture_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    for item in dados:
        email = item['email'].strip()
        nome = item['nome'].strip()
        # Define o username como a parte do e-mail antes do @
        username = email.split('@')[0]
        
        Usuario.objects.get_or_create(
            username=username,
            defaults={
                'first_name': nome[:150],
                'email': email,
                'perfil': 'professor',
                'password': make_password('ifmg@123'),
                'deve_trocar_senha': True
            }
        )

def remover_professores(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    # Remove apenas usuários com perfil professor e o domínio de e-mail institucional
    Usuario.objects.filter(perfil='professor', email__endswith='@ifmg.edu.br').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('atendimentos', '0005_ajuste_aluno_monitor_opcional'),
        ('accounts', '0001_initial'), # Garante que o modelo Usuario base exista
    ]

    operations = [
        migrations.RunPython(carregar_professores, reverse_code=remover_professores),
    ]