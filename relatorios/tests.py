from datetime import datetime

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo
from curriculum.models import Disciplina, Turma


class RelatoriosE2ETests(TestCase):
    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(nome="Banco de Dados", codigo="BD102", curso="Ciência da Computação")

        self.professor = Usuario.objects.create_user(
            username="prof2",
            password="pass123",
            perfil="professor",
            email="prof2@example.com",
        )
        self.turma = Turma.objects.create(disciplina=self.disciplina, semestre="2026/1", professor=self.professor)

        self.monitor_user = Usuario.objects.create_user(
            username="mon10",
            password="pass123",
            perfil="monitor",
            email="mon10@example.com",
        )
        self.monitor = Monitor.objects.create(usuario=self.monitor_user, turma=self.turma, ativo=True)
        self.aluno = Aluno.objects.create(monitor=self.monitor, nome="Eva", matricula="E010")

        self.client.login(username="mon10", password="pass123")

        dt = timezone.now()
        self.at_ind = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.disciplina,
            data_hora=dt,
            duracao_min=45,
            topico="Normalização",
            observacoes="",
        )

        self.at_gr = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=self.disciplina,
            data_hora=dt,
            duracao_min=60,
            topico="Projetos coletivos",
            observacoes="",
        )
        TutoriaGrupo.objects.create(atendimento=self.at_gr, numero_participantes=4)

        self.client.logout()

    def login_professor(self):
        self.client.login(username="prof2", password="pass123")

    def test_professor_dashboard_mostra_totais(self):
        self.login_professor()
        resp = self.client.get(reverse("relatorios:dashboard_professor"))
        self.assertEqual(resp.status_code, 200)
        # Total do mês deve ser pelo menos 2 (1 individual + 1 grupo).
        self.assertContains(resp, "2")

    def test_exportar_pdf_retornar_application_pdf(self):
        self.login_professor()
        today = timezone.now().date()
        url = reverse("relatorios:exportar_pdf")
        resp = self.client.get(
            url,
            {
                "data_inicio": today.strftime("%Y-%m-%d"),
                "data_fim": today.strftime("%Y-%m-%d"),
                "tipo": "",
                "monitor": "",
                "disciplina": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")


class RelatoriosAnualMonitorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(nome="Banco de Dados", codigo="BD102", curso="Ciência da Computação")
        self.professor = Usuario.objects.create_user(
            username="prof_anual",
            password="pass123",
            perfil="professor",
            email="prof_anual@example.com",
        )
        self.turma = Turma.objects.create(disciplina=self.disciplina, semestre="2026/1", professor=self.professor)
        self.monitor_user = Usuario.objects.create_user(
            username="mon_anual",
            password="pass123",
            perfil="monitor",
            email="mon_anual@example.com",
        )
        self.monitor = Monitor.objects.create(usuario=self.monitor_user, turma=self.turma, ativo=True)
        self.aluno = Aluno.objects.create(monitor=self.monitor, nome="João", matricula="J001")

        self.atendimento1 = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.disciplina,
            data_hora=timezone.make_aware(datetime(2026, 1, 15, 10, 0)),
            duracao_min=60,
            topico="Revisão A",
            observacoes="",
        )
        self.atendimento2 = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=self.disciplina,
            data_hora=timezone.make_aware(datetime(2026, 2, 20, 14, 0)),
            duracao_min=90,
            topico="Revisão B",
            observacoes="",
        )
        TutoriaGrupo.objects.create(atendimento=self.atendimento2, numero_participantes=3)

    def test_relatorio_anual_monitor_exibe_totais(self):
        self.client.login(username="mon_anual", password="pass123")
        resp = self.client.get(reverse("relatorios:relatorio_anual_monitor"), {"year": "2026"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_count"], 2)
        self.assertEqual(resp.context["total_hours"], 2.5)
        self.assertContains(resp, "Revisão A")
        self.assertContains(resp, "Revisão B")
        self.assertContains(resp, "Jan")
        self.assertContains(resp, "Fev")

    def test_exportar_pdf_relatorio_anual_monitor(self):
        self.client.login(username="mon_anual", password="pass123")
        resp = self.client.get(reverse("relatorios:exportar_pdf_relatorio_anual"), {"year": "2026"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertGreater(len(resp.content), 1000)

