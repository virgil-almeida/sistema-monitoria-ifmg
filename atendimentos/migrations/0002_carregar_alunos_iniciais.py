import json
import os
from django.db import migrations
from django.conf import settings

def carregar_fixtures(apps, schema_editor):
    Aluno = apps.get_model('atendimentos', 'Aluno')
    # Caminho para o arquivo JSON dentro da pasta da app
    fixture_path = os.path.join(settings.BASE_DIR, 'atendimentos', 'fixtures', 'alunos_iniciais.json')
    
    if not os.path.exists(fixture_path):
        return

    with open(fixture_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    for item in dados:
        # O item é uma lista: ["Nome - Matricula - Turma", null, ...]
        linha_bruta = item[0]
        partes = linha_bruta.split(' - ')
        
        if len(partes) >= 2:
            nome = partes[0].strip()
            matricula = partes[1].strip()
            
            # Usa get_or_create para evitar erros se a migration for rodada novamente
            Aluno.objects.get_or_create(
                matricula=matricula,
                defaults={'nome': nome}
            )

def remover_fixtures(apps, schema_editor):
    Aluno = apps.get_model('atendimentos', 'Aluno')
    # Remove apenas os alunos que não possuem monitor (os da carga inicial)
    Aluno.objects.filter(monitor__isnull=True).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('atendimentos', '0001_initial'), # Certifique-se que o nome da migration anterior está correto
    ]

    operations = [
        migrations.RunPython(carregar_fixtures, reverse_code=remover_fixtures),
    ]