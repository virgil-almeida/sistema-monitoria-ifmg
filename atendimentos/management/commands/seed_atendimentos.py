"""
Comando para popular o banco com atendimentos de teste.

Uso:
    python manage.py seed_atendimentos               # 50 atendimentos
    python manage.py seed_atendimentos --total 100   # quantidade personalizada
    python manage.py seed_atendimentos --monitor 3   # apenas para um monitor específico
    python manage.py seed_atendimentos --dias 90     # distribuídos nos últimos N dias (padrão: 60)
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo


TOPICOS = [
    "Revisão de prova", "Exercícios de fixação", "Dúvidas sobre lista",
    "Introdução ao conteúdo", "Resolução de trabalho", "Preparação para prova",
    "Correção de exercícios", "Conceitos fundamentais", "Aplicações práticas",
    "Dificuldades no projeto", "Revisão de fórmulas", "Estudo dirigido",
    "Resolução de problemas", "Dúvidas pós-aula", "Apoio em laboratório",
    "Revisão de conceitos", "Exercícios adicionais", "Nivelamento",
    "Apoio para recuperação", "Simulado comentado",
]

OBSERVACOES = [
    "Aluno apresentou boa evolução.", "Necessita de mais prática.",
    "Conceitos bem assimilados.", "Retornar na próxima semana.",
    "Dificuldade com a parte teórica.", "Ótimo aproveitamento da sessão.",
    "", "", "",  # vazio com maior frequência
]

DURACOES = [30, 45, 60, 90, 120]


class Command(BaseCommand):
    help = "Cria atendimentos de teste."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=50,
                            help="Quantidade de atendimentos (padrão: 50).")
        parser.add_argument("--monitor", type=int, default=None,
                            help="ID do monitor (padrão: todos os monitores ativos).")
        parser.add_argument("--dias", type=int, default=60,
                            help="Janela de datas em dias a partir de hoje (padrão: 60).")

    def handle(self, *args, **options):
        total = options["total"]
        monitor_id = options["monitor"]
        dias = options["dias"]

        if monitor_id:
            monitores = list(Monitor.objects.filter(pk=monitor_id, ativo=True)
                             .select_related("turma__disciplina"))
            if not monitores:
                raise CommandError(f"Monitor id={monitor_id} não encontrado ou inativo.")
        else:
            monitores = list(Monitor.objects.filter(ativo=True)
                             .select_related("turma__disciplina"))

        if not monitores:
            raise CommandError("Nenhum monitor ativo encontrado.")

        agora = timezone.now()
        criados_ind = criados_grp = 0

        for _ in range(total):
            monitor = random.choice(monitores)
            disciplina = monitor.turma.disciplina
            delta = timedelta(
                days=random.randint(0, dias),
                hours=random.randint(7, 18),
                minutes=random.choice([0, 15, 30, 45]),
            )
            data_hora = agora - delta
            duracao = random.choice(DURACOES)
            topico = random.choice(TOPICOS)
            obs = random.choice(OBSERVACOES)

            alunos_monitor = list(monitor.alunos.all())
            # 70 % individual (se houver alunos), 30 % grupo
            if alunos_monitor and random.random() < 0.7:
                aluno = random.choice(alunos_monitor)
                Atendimento.objects.create(
                    monitor=monitor,
                    tipo=Atendimento.TIPO_INDIVIDUAL,
                    aluno=aluno,
                    disciplina=disciplina,
                    data_hora=data_hora,
                    duracao_min=duracao,
                    topico=topico,
                    observacoes=obs,
                )
                criados_ind += 1
            else:
                at = Atendimento.objects.create(
                    monitor=monitor,
                    tipo=Atendimento.TIPO_GRUPO,
                    aluno=None,
                    disciplina=disciplina,
                    data_hora=data_hora,
                    duracao_min=duracao,
                    topico=topico,
                    observacoes=obs,
                )
                TutoriaGrupo.objects.create(
                    atendimento=at,
                    numero_participantes=random.randint(2, 15),
                )
                criados_grp += 1

        self.stdout.write(self.style.SUCCESS(
            f"{criados_ind + criados_grp} atendimento(s) criado(s)  "
            f"({criados_ind} individuais, {criados_grp} em grupo)."
        ))
