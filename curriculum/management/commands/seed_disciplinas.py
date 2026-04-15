"""
Comando para popular o banco com disciplinas de teste.

Uso:
    python manage.py seed_disciplinas                # 50 disciplinas
    python manage.py seed_disciplinas --total 20     # quantidade personalizada
    python manage.py seed_disciplinas --limpar       # remove disciplinas sem turmas antes de criar
"""

from django.core.management.base import BaseCommand

from curriculum.models import Disciplina


DISCIPLINAS = [
    # (codigo_base, nome, curso)
    ("MAT", "Cálculo I", "Engenharia"),
    ("MAT", "Cálculo II", "Engenharia"),
    ("MAT", "Cálculo III", "Engenharia"),
    ("MAT", "Álgebra Linear", "Engenharia"),
    ("MAT", "Equações Diferenciais", "Engenharia"),
    ("MAT", "Estatística e Probabilidade", "Engenharia"),
    ("FIS", "Física I — Mecânica", "Engenharia"),
    ("FIS", "Física II — Eletromagnetismo", "Engenharia"),
    ("FIS", "Física III — Ótica e Ondas", "Engenharia"),
    ("QUI", "Química Geral", "Engenharia"),
    ("ALG", "Algoritmos e Lógica de Programação", "Sistemas de Informação"),
    ("ALG", "Estruturas de Dados", "Sistemas de Informação"),
    ("ALG", "Algoritmos em Grafos", "Sistemas de Informação"),
    ("POO", "Programação Orientada a Objetos", "Sistemas de Informação"),
    ("WEB", "Desenvolvimento Web", "Sistemas de Informação"),
    ("BD1", "Banco de Dados I", "Sistemas de Informação"),
    ("BD2", "Banco de Dados II", "Sistemas de Informação"),
    ("SO1", "Sistemas Operacionais", "Sistemas de Informação"),
    ("RED", "Redes de Computadores", "Sistemas de Informação"),
    ("SEG", "Segurança da Informação", "Sistemas de Informação"),
    ("ENG", "Engenharia de Software", "Sistemas de Informação"),
    ("IHC", "Interface Humano-Computador", "Sistemas de Informação"),
    ("COM", "Compiladores", "Ciência da Computação"),
    ("ARQ", "Arquitetura de Computadores", "Ciência da Computação"),
    ("PAR", "Computação Paralela e Distribuída", "Ciência da Computação"),
    ("IA1", "Inteligência Artificial", "Ciência da Computação"),
    ("ML1", "Aprendizado de Máquina", "Ciência da Computação"),
    ("VIS", "Visão Computacional", "Ciência da Computação"),
    ("PLC", "Linguagens de Programação", "Ciência da Computação"),
    ("TEO", "Teoria da Computação", "Ciência da Computação"),
    ("ADM", "Introdução à Administração", "Administração"),
    ("ADM", "Gestão de Projetos", "Administração"),
    ("ADM", "Contabilidade Geral", "Administração"),
    ("ADM", "Marketing Digital", "Administração"),
    ("ADM", "Empreendedorismo", "Administração"),
    ("ECO", "Microeconomia", "Administração"),
    ("ECO", "Macroeconomia", "Administração"),
    ("FIN", "Finanças Empresariais", "Administração"),
    ("RH1", "Gestão de Pessoas", "Administração"),
    ("LOG", "Logística e Cadeia de Suprimentos", "Administração"),
    ("ELE", "Circuitos Elétricos I", "Engenharia Elétrica"),
    ("ELE", "Circuitos Elétricos II", "Engenharia Elétrica"),
    ("ELE", "Eletrônica Analógica", "Engenharia Elétrica"),
    ("ELE", "Eletrônica Digital", "Engenharia Elétrica"),
    ("SIN", "Sinais e Sistemas", "Engenharia Elétrica"),
    ("POT", "Eletrônica de Potência", "Engenharia Elétrica"),
    ("CON", "Controle e Automação", "Engenharia Elétrica"),
    ("MEC", "Resistência dos Materiais", "Engenharia Mecânica"),
    ("MEC", "Termodinâmica", "Engenharia Mecânica"),
    ("MEC", "Mecânica dos Fluidos", "Engenharia Mecânica"),
]


class Command(BaseCommand):
    help = "Cria disciplinas de teste."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=50,
            help="Quantidade de disciplinas a criar (padrão: 50, máx: 50).",
        )
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove disciplinas sem turmas antes de criar as novas.",
        )

    def handle(self, *args, **options):
        total = min(options["total"], len(DISCIPLINAS))
        limpar = options["limpar"]

        if limpar:
            sem_turma = Disciplina.objects.filter(turmas__isnull=True)
            removidas = sem_turma.count()
            sem_turma.delete()
            self.stdout.write(self.style.WARNING(f"{removidas} disciplina(s) sem turma removida(s)."))

        criadas = 0
        for codigo_base, nome, curso in DISCIPLINAS[:total]:
            seq = str(criadas + 101)
            codigo = f"{codigo_base}{seq}"
            _, created = Disciplina.objects.get_or_create(
                codigo=codigo,
                curso=curso,
                defaults={"nome": nome},
            )
            if created:
                criadas += 1

        self.stdout.write(self.style.SUCCESS(f"{criadas} disciplina(s) criada(s) com sucesso."))
