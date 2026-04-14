"""
Comando para popular o banco com alunos de teste.

Uso:
    python manage.py seed_alunos                  # 50 alunos no primeiro monitor ativo
    python manage.py seed_alunos --monitor 3      # monitor específico pelo id
    python manage.py seed_alunos --total 100      # quantidade personalizada
    python manage.py seed_alunos --limpar         # remove alunos sem atendimentos antes de criar
"""

import random
import string

from django.core.management.base import BaseCommand, CommandError

from atendimentos.models import Aluno, Monitor


NOMES = [
    "Ana", "Bruno", "Carlos", "Daniela", "Eduardo", "Fernanda", "Gabriel",
    "Helena", "Igor", "Juliana", "Kevin", "Larissa", "Marcos", "Natália",
    "Otávio", "Paula", "Rafael", "Sabrina", "Thiago", "Ursula", "Vinicius",
    "Wendy", "Xavier", "Yasmin", "Zeca", "Alice", "Beatriz", "Caio",
    "Diana", "Emanuel", "Flávia", "Gustavo", "Isabela", "João", "Karla",
    "Leonardo", "Mariana", "Nicolas", "Olívia", "Pedro", "Quésia", "Rodrigo",
    "Sofia", "Túlio", "Valentina", "William", "Xuxa", "Yago", "Zara", "Afonso",
]

SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa",
    "Ferreira", "Rodrigues", "Almeida", "Nascimento", "Carvalho", "Freitas",
    "Barbosa", "Ribeiro", "Martins", "Melo", "Araújo", "Gomes", "Lopes",
    "Monteiro", "Castro", "Cardoso", "Moreira", "Nunes", "Pinto", "Moraes",
    "Correia", "Teixeira", "Mendes",
]


def _matricula_aleatoria(prefixo: str) -> str:
    ano = random.randint(2019, 2025)
    seq = random.randint(1, 9999)
    return f"{prefixo}{ano}{seq:04d}"


def _email(nome: str, sobrenome: str) -> str:
    dominio = random.choice(["gmail.com", "hotmail.com", "ifmg.edu.br", "outlook.com"])
    sufixo = "".join(random.choices(string.digits, k=2))
    return f"{nome.lower()}.{sobrenome.lower()}{sufixo}@{dominio}"


class Command(BaseCommand):
    help = "Cria alunos de teste para um monitor."

    def add_arguments(self, parser):
        parser.add_argument(
            "--monitor",
            type=int,
            default=None,
            help="ID do monitor (padrão: primeiro monitor ativo encontrado).",
        )
        parser.add_argument(
            "--total",
            type=int,
            default=50,
            help="Quantidade de alunos a criar (padrão: 50).",
        )
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove alunos sem nenhum atendimento antes de criar os novos.",
        )

    def handle(self, *args, **options):
        monitor_id = options["monitor"]
        total = options["total"]
        limpar = options["limpar"]

        if monitor_id:
            try:
                monitor = Monitor.objects.select_related("usuario", "turma__disciplina").get(pk=monitor_id)
            except Monitor.DoesNotExist:
                raise CommandError(f"Monitor com id={monitor_id} não encontrado.")
        else:
            monitor = Monitor.objects.filter(ativo=True).select_related("usuario", "turma__disciplina").first()
            if not monitor:
                raise CommandError(
                    "Nenhum monitor ativo encontrado. Crie um monitor antes de executar este comando."
                )

        self.stdout.write(f"Monitor: {monitor.usuario.username} — {monitor.turma.disciplina}")

        if limpar:
            sem_atendimento = monitor.alunos.filter(atendimentos__isnull=True)
            removidos = sem_atendimento.count()
            sem_atendimento.delete()
            self.stdout.write(self.style.WARNING(f"  {removidos} aluno(s) sem atendimento removido(s)."))

        matriculas_existentes = set(monitor.alunos.values_list("matricula", flat=True))
        prefixo = monitor.turma.disciplina.codigo[:3].upper()

        criados = 0
        tentativas = 0
        while criados < total and tentativas < total * 10:
            tentativas += 1
            nome = random.choice(NOMES)
            sobrenome = random.choice(SOBRENOMES)
            nome_completo = f"{nome} {sobrenome}"
            matricula = _matricula_aleatoria(prefixo)

            if matricula in matriculas_existentes:
                continue

            matriculas_existentes.add(matricula)
            Aluno.objects.create(
                monitor=monitor,
                nome=nome_completo,
                matricula=matricula,
                email=_email(nome, sobrenome),
            )
            criados += 1

        self.stdout.write(self.style.SUCCESS(f"  {criados} aluno(s) criado(s) com sucesso."))

        if criados < total:
            self.stdout.write(
                self.style.WARNING(f"  Atenção: só foi possível criar {criados}/{total} (matrículas duplicadas evitadas).")
            )
