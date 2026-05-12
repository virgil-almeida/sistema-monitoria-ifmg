"""
Testes de integração end-to-end — Issue #18

Cobrem os 4 fluxos principais do sistema de ponta a ponta:

  1. Monitor autentica, registra atendimento individual e vê na listagem.
  2. Monitor registra tutoria em grupo; professor vê totais no dashboard.
  3. Professor filtra relatório por período e exporta PDF.
  4. Admin cadastra disciplina, turma e vincula monitor; monitor acessa atendimentos.
"""

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo
from curriculum.models import Disciplina, Turma


class E2EFluxo1MonitorAtendimentoIndividual(TestCase):
    """
    Fluxo 1: Monitor autentica → registra atendimento individual → aparece na listagem.
    """

    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(
            nome="Cálculo I", codigo="MAT101", curso="Engenharia"
        )
        self.professor = Usuario.objects.create_user(
            username="prof_e2e1", password="pass123", perfil="professor"
        )
        self.turma = Turma.objects.create(
            disciplina=self.disciplina, semestre="2026/1", professor=self.professor
        )
        self.monitor_user = Usuario.objects.create_user(
            username="mon_e2e1", password="pass123", perfil="monitor"
        )
        self.monitor = Monitor.objects.create(
            usuario=self.monitor_user, turma=self.turma, ativo=True
        )

    def test_fluxo_completo_individual(self):
        # 1. Login
        logged = self.client.login(username="mon_e2e1", password="pass123")
        self.assertTrue(logged)

        # 2. Acessa a página de registro (deve retornar 200)
        resp = self.client.get(reverse("atendimentos:criar_atendimento_individual"))
        self.assertEqual(resp.status_code, 200)

        # 3. Envia o formulário criando um aluno inline
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")
        resp = self.client.post(
            reverse("atendimentos:criar_atendimento_individual"),
            {
                "monitor": self.monitor.id,
                "aluno": "",
                "novo_aluno_nome": "Fernanda",
                "novo_aluno_matricula": "F001",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 60,
                "topico": "Derivadas e integrais",
                "observacoes": "",
            },
            follow=True,
        )

        # 4. Redirecionou para a listagem com sucesso
        self.assertEqual(resp.status_code, 200)
        self.assertRedirects(
            self.client.post(
                reverse("atendimentos:criar_atendimento_individual"),
                {
                    "monitor": self.monitor.id,
                    "aluno": "",
                    "novo_aluno_nome": "Fernanda2",
                    "novo_aluno_matricula": "F002",
                    "novo_aluno_email": "",
                    "data_hora": dt,
                    "duracao_min": 30,
                    "topico": "Limites",
                    "observacoes": "",
                },
            ),
            reverse("atendimentos:lista_meus_atendimentos"),
        )

        # 5. Aluno e atendimento foram criados
        self.assertTrue(
            Aluno.objects.filter(monitor=self.monitor, matricula="F001").exists()
        )
        self.assertTrue(
            Atendimento.objects.filter(
                monitor=self.monitor,
                tipo=Atendimento.TIPO_INDIVIDUAL,
                topico="Derivadas e integrais",
            ).exists()
        )

        # 6. Aparece na listagem
        resp_lista = self.client.get(reverse("atendimentos:lista_meus_atendimentos"))
        self.assertEqual(resp_lista.status_code, 200)
        self.assertContains(resp_lista, "Derivadas e integrais")
        self.assertContains(resp_lista, "Limites")


class E2EFluxo2GrupoProfessorDashboard(TestCase):
    """
    Fluxo 2: Monitor registra tutoria em grupo → professor vê totais no dashboard.
    """

    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(
            nome="Física I", codigo="FIS101", curso="Engenharia"
        )
        self.professor = Usuario.objects.create_user(
            username="prof_e2e2", password="pass123", perfil="professor"
        )
        self.turma = Turma.objects.create(
            disciplina=self.disciplina, semestre="2026/1", professor=self.professor
        )
        self.monitor_user = Usuario.objects.create_user(
            username="mon_e2e2", password="pass123", perfil="monitor"
        )
        self.monitor = Monitor.objects.create(
            usuario=self.monitor_user, turma=self.turma, ativo=True
        )

    def test_fluxo_grupo_aparece_no_dashboard(self):
        # 1. Monitor loga e registra tutoria em grupo
        self.client.login(username="mon_e2e2", password="pass123")

        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")
        resp = self.client.post(
            reverse("atendimentos:criar_atendimento_grupo"),
            {
                "monitor": self.monitor.id,
                "data_hora": dt,
                "duracao_min": 90,
                "topico": "Leis de Newton",
                "observacoes": "Revisão pré-prova",
                "numero_participantes": 5,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        # Verifica que o atendimento foi criado com TutoriaGrupo
        atendimento = Atendimento.objects.get(
            monitor=self.monitor, tipo=Atendimento.TIPO_GRUPO
        )
        self.assertEqual(atendimento.tutoria_grupo.numero_participantes, 5)

        # 2. Professor loga e acessa o dashboard
        self.client.logout()
        self.client.login(username="prof_e2e2", password="pass123")

        resp_dash = self.client.get(reverse("relatorios:dashboard_professor"))
        self.assertEqual(resp_dash.status_code, 200)

        # 3. O total do mês deve incluir o atendimento em grupo
        # O dashboard exibe `total_mes` no contexto
        self.assertGreaterEqual(resp_dash.context["total_mes"], 1)
        self.assertContains(resp_dash, "1")  # pelo menos 1 atendimento


class E2EFluxo3ProfessorFiltraEExportaPDF(TestCase):
    """
    Fluxo 3: Professor filtra relatório por período → exporta PDF com os mesmos filtros.
    """

    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(
            nome="Química", codigo="QUI101", curso="Engenharia"
        )
        self.professor = Usuario.objects.create_user(
            username="prof_e2e3", password="pass123", perfil="professor"
        )
        self.turma = Turma.objects.create(
            disciplina=self.disciplina, semestre="2026/1", professor=self.professor
        )
        self.monitor_user = Usuario.objects.create_user(
            username="mon_e2e3", password="pass123", perfil="monitor"
        )
        self.monitor = Monitor.objects.create(
            usuario=self.monitor_user, turma=self.turma, ativo=True
        )
        self.aluno = Aluno.objects.create(
            monitor=self.monitor, nome="Guilherme", matricula="G001"
        )

        # Cria atendimentos no mês atual
        self.hoje = timezone.now()
        Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.disciplina,
            data_hora=self.hoje,
            duracao_min=45,
            topico="Estequiometria",
            observacoes="",
        )
        Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=self.disciplina,
            data_hora=self.hoje,
            duracao_min=60,
            topico="Tabela periódica",
            observacoes="",
        )

    def test_fluxo_filtro_e_exportacao_pdf(self):
        self.client.login(username="prof_e2e3", password="pass123")

        hoje_local = timezone.localdate()
        filtros = {
            "data_inicio": hoje_local.isoformat(),
            "data_fim": hoje_local.isoformat(),
            "tipo": "",
            "monitor": "",
            "disciplina": "",
        }

        # 1. Acessa relatório filtrado e verifica resultados
        resp = self.client.get(reverse("relatorios:relatorio_avancado"), filtros)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.context["qs_total"], 2)
        self.assertContains(resp, "Estequiometria")
        self.assertContains(resp, "Tabela periódica")

        # 2. Exporta PDF com os mesmos filtros
        resp_pdf = self.client.get(reverse("relatorios:exportar_pdf"), filtros)
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf["Content-Type"], "application/pdf")
        # Verifica que o PDF não está vazio
        self.assertGreater(len(resp_pdf.content), 1000)


class E2EFluxo4AdminCadastraDisciplinaEVinculaMonitor(TestCase):
    """
    Fluxo 4: Admin cadastra disciplina, cria turma, vincula monitor →
    monitor loga e consegue acessar atendimentos.
    """

    def setUp(self):
        self.client = Client()

        # Usuário admin (perfil=admin, não superuser)
        self.admin_user = Usuario.objects.create_user(
            username="admin_e2e4", password="pass123", perfil="admin"
        )
        # Professor necessário para criar turma
        self.professor = Usuario.objects.create_user(
            username="prof_e2e4", password="pass123", perfil="professor"
        )
        # Usuário monitor (sem Monitor record ainda)
        self.monitor_user = Usuario.objects.create_user(
            username="mon_e2e4", password="pass123", perfil="monitor"
        )

    def test_fluxo_admin_cria_estrutura_e_monitor_acessa(self):
        # 1. Admin loga
        self.client.login(username="admin_e2e4", password="pass123")

        # 2. Admin cria disciplina
        resp = self.client.post(
            reverse("curriculum:disciplinas_create"),
            {"nome": "Algoritmos e Estruturas de Dados", "codigo": "AED201", "curso": "Sistemas de Informação"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            Disciplina.objects.filter(codigo="AED201").exists()
        )
        disciplina = Disciplina.objects.get(codigo="AED201")

        # 3. Admin cria turma
        resp = self.client.post(
            reverse("curriculum:turmas_create"),
            {
                "disciplina": disciplina.id,
                "semestre": "2026/1",
                "professor": self.professor.id,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            Turma.objects.filter(disciplina=disciplina, semestre="2026/1").exists()
        )
        turma = Turma.objects.get(disciplina=disciplina, semestre="2026/1")

        # 4. Admin vincula monitor à turma via interface de monitores
        resp = self.client.post(
            reverse("curriculum:monitores_create"),
            {
                "usuario": self.monitor_user.id,
                "turma": turma.id,
                "ativo": True,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            Monitor.objects.filter(usuario=self.monitor_user, turma=turma, ativo=True).exists()
        )

        # 5. Monitor loga e acessa a listagem de atendimentos (sem erro de permissão)
        self.client.logout()
        self.client.login(username="mon_e2e4", password="pass123")

        resp_lista = self.client.get(reverse("atendimentos:lista_meus_atendimentos"))
        self.assertEqual(resp_lista.status_code, 200)

        # 6. Monitor consegue acessar o formulário de atendimento individual
        resp_form = self.client.get(reverse("atendimentos:criar_atendimento_individual"))
        self.assertEqual(resp_form.status_code, 200)

        # 7. Monitor registra um atendimento inline
        monitor = Monitor.objects.get(usuario=self.monitor_user)
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")
        resp_post = self.client.post(
            reverse("atendimentos:criar_atendimento_individual"),
            {
                "monitor": monitor.id,
                "aluno": "",
                "novo_aluno_nome": "Helena",
                "novo_aluno_matricula": "H001",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 50,
                "topico": "Árvores binárias",
                "observacoes": "",
            },
            follow=True,
        )
        self.assertEqual(resp_post.status_code, 200)
        self.assertTrue(
            Atendimento.objects.filter(
                monitor__usuario=self.monitor_user,
                topico="Árvores binárias",
            ).exists()
        )
        self.assertContains(resp_post, "Árvores binárias")
