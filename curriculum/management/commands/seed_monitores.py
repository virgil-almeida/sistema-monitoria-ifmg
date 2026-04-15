"""
Comando para popular o banco com monitores de teste.

Cria usuários com perfil='monitor' e os vincula a turmas existentes.
Se não houver turmas suficientes, cria turmas e disciplinas extras automaticamente.

Uso:
    python manage.py seed_monitores              # 10 monitores
    python manage.py seed_monitores --total 5    # quantidade personalizada
"""

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Usuario
from atendimentos.models import Monitor
from curriculum.models import Disciplina, Turma


NOMES_MONITOR = [
    ("monitor01", "André", "Souza"),
    ("monitor02", "Bianca", "Lima"),
    ("monitor03", "Caio", "Ferreira"),
    ("monitor04", "Débora", "Alves"),
    ("monitor05", "Erick", "Nunes"),
    ("monitor06", "Fabiana", "Castro"),
    ("monitor07", "Guilherme", "Pereira"),
    ("monitor08", "Hanna", "Ribeiro"),
    ("monitor09", "Ivan", "Moreira"),
    ("monitor10", "Joana", "Martins"),
    ("monitor11", "Kaique", "Barbosa"),
    ("monitor12", "Letícia", "Campos"),
]

SEMESTRES_EXTRA = ["2025/1", "2025/2", "2026/1", "2026/2"]


def _garantir_turmas(qtd_necessaria, professor):
    """Garante que existam pelo menos `qtd_necessaria` turmas no banco."""
    turmas = list(Turma.objects.select_related("disciplina").all())
    if len(turmas) >= qtd_necessaria:
        return turmas

    disciplinas = list(Disciplina.objects.all())
    if not disciplinas:
        disciplinas = [
            Disciplina.objects.create(nome="Disciplina Extra", codigo="EXT101", curso="Geral")
        ]

    i = 0
    for semestre in SEMESTRES_EXTRA:
        for disciplina in disciplinas:
            if len(turmas) >= qtd_necessaria:
                break
            turma, created = Turma.objects.get_or_create(
                disciplina=disciplina,
                semestre=semestre,
                defaults={"professor": professor},
            )
            if created:
                turmas.append(turma)
        if len(turmas) >= qtd_necessaria:
            break

    return turmas


class Command(BaseCommand):
    help = "Cria monitores de teste (usuários + vínculos com turmas)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=10,
            help="Quantidade de monitores a criar (padrão: 10, máx: 12).",
        )

    def handle(self, *args, **options):
        total = min(options["total"], len(NOMES_MONITOR))

        professor = Usuario.objects.filter(perfil="professor").first()
        if not professor:
            raise CommandError(
                "Nenhum professor encontrado. Crie ao menos um usuário com perfil='professor' antes."
            )

        turmas = _garantir_turmas(total, professor)
        if not turmas:
            raise CommandError("Não foi possível obter turmas para vincular os monitores.")

        criados = 0
        for i, (username, primeiro, ultimo) in enumerate(NOMES_MONITOR[:total]):
            usuario, user_criado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": primeiro,
                    "last_name": ultimo,
                    "email": f"{username}@ifmg.edu.br",
                    "perfil": "monitor",
                    "password": make_password("monitor123"),
                },
            )
            if not user_criado and usuario.perfil != "monitor":
                self.stdout.write(self.style.WARNING(
                    f"  Usuário '{username}' já existe com perfil='{usuario.perfil}'. Pulando."
                ))
                continue

            turma = turmas[i % len(turmas)]
            monitor, mon_criado = Monitor.objects.get_or_create(
                usuario=usuario,
                turma=turma,
                defaults={"ativo": True},
            )

            if mon_criado:
                criados += 1
                self.stdout.write(f"  + {username} → {turma.disciplina.codigo} ({turma.semestre})")
            else:
                self.stdout.write(self.style.WARNING(
                    f"  Monitor '{username}' já vinculado a esta turma. Pulando."
                ))

        self.stdout.write(self.style.SUCCESS(f"\n{criados} monitor(es) criado(s). Senha padrão: monitor123"))
