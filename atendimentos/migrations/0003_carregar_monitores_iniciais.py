import json
import os
from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password

def carregar_monitores(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    Monitor = apps.get_model('atendimentos', 'Monitor')
    Turma = apps.get_model('curriculum', 'Turma')
    Disciplina = apps.get_model('curriculum', 'Disciplina')

    fixture_path = os.path.join(settings.BASE_DIR, 'atendimentos', 'fixtures', 'monitories_iniciais.json')
    
    if not os.path.exists(fixture_path):
        return

    with open(fixture_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # Precisamos de um professor para criar turmas caso elas não existam
    professor = Usuario.objects.filter(perfil='professor').first()

    for item in dados:
        linha_bruta = item[0]
        partes = [p.strip() for p in linha_bruta.split(' - ')]
        
        if len(partes) >= 3:
            nome = partes[0]
            matricula = partes[-1]
            nome_disciplina = " - ".join(partes[1:-1])

            # 1. Criar ou obter o Usuário para o Monitor
            usuario, _ = Usuario.objects.get_or_create(
                username=matricula,
                defaults={
                    'first_name': nome[:30],
                    'email': f"{matricula}@academico.ifmg.edu.br",
                    'perfil': 'monitor',
                    'password': make_password('ifmg@123'),
                    'deve_trocar_senha': True
                }
            )

            # 2. Garantir que a Disciplina e Turma existam
            disciplina, _ = Disciplina.objects.get_or_create(
                nome__icontains=nome_disciplina,
                defaults={'nome': nome_disciplina, 'codigo': matricula[:6], 'curso': 'Geral'}
            )
            
            turma = Turma.objects.filter(disciplina=disciplina).first()
            if not turma and professor:
                turma = Turma.objects.create(
                    disciplina=disciplina,
                    semestre='2024/1',
                    professor=professor
                )

            # 3. Criar o registro de Monitor
            if turma:
                Monitor.objects.get_or_create(
                    usuario=usuario,
                    turma=turma,
                    defaults={'ativo': True}
                )

def remover_monitores(apps, schema_editor):
    Monitor = apps.get_model('atendimentos', 'Monitor')
    Usuario = apps.get_model('accounts', 'Usuario')
    
    # Remove apenas os monitores e usuários criados via carga inicial
    # para evitar deletar dados inseridos manualmente depois.
    Monitor.objects.all().delete()
    Usuario.objects.filter(
        perfil='monitor', 
        email__endswith='@academico.ifmg.edu.br'
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('atendimentos', '0002_carregar_alunos_iniciais'),
    ]

    operations = [
        migrations.RunPython(carregar_monitores, reverse_code=remover_monitores),
    ]