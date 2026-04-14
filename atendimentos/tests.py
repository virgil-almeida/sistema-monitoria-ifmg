from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo
from curriculum.models import Disciplina, Turma


class AtendimentosSprint2Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.disciplina = Disciplina.objects.create(nome="Algoritmos", codigo="ALG101", curso="Ciência da Computação")

        self.professor = Usuario.objects.create_user(
            username="prof1",
            password="pass123",
            perfil="professor",
            email="prof1@example.com",
        )
        self.turma = Turma.objects.create(disciplina=self.disciplina, semestre="2026/1", professor=self.professor)

        self.monitor_user = Usuario.objects.create_user(
            username="mon1",
            password="pass123",
            perfil="monitor",
            email="mon1@example.com",
        )
        self.monitor = Monitor.objects.create(usuario=self.monitor_user, turma=self.turma, ativo=True)

        self.outro_monitor_user = Usuario.objects.create_user(
            username="mon2",
            password="pass123",
            perfil="monitor",
            email="mon2@example.com",
        )
        self.outro_monitor_turma = Turma.objects.create(
            disciplina=self.disciplina,
            semestre="2026/2",
            professor=self.professor,
        )
        self.outro_monitor = Monitor.objects.create(usuario=self.outro_monitor_user, turma=self.outro_monitor_turma, ativo=True)

        self.aluno = Aluno.objects.create(monitor=self.monitor, nome="Alice", matricula="A001", email="alice@example.com")
        self.aluno_outro = Aluno.objects.create(monitor=self.outro_monitor, nome="Bob", matricula="B001")

    def login_monitor(self):
        self.client.login(username="mon1", password="pass123")

    def login_professor(self):
        self.client.login(username="prof1", password="pass123")

    def test_monitor_nao_eboleto_professor_nega_acesso(self):
        # Professor tenta acessar endpoints de monitor.
        self.login_professor()
        resp = self.client.get(reverse("atendimentos:lista_meus_atendimentos"))
        self.assertEqual(resp.status_code, 403)

    def test_criar_atendimento_individual_com_aluno_existente(self):
        self.login_monitor()
        url = reverse("atendimentos:criar_atendimento_individual")
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")

        resp = self.client.post(
            url,
            {
                "aluno": self.aluno.id,
                "novo_aluno_nome": "",
                "novo_aluno_matricula": "",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 60,
                "topico": "Revisão de provas",
                "observacoes": "Sem observações",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Atendimento.objects.filter(monitor=self.monitor, tipo=Atendimento.TIPO_INDIVIDUAL, aluno=self.aluno).exists())
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Revisão de provas")

    def test_criar_atendimento_individual_inline_cria_aluno(self):
        self.login_monitor()
        url = reverse("atendimentos:criar_atendimento_individual")
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")

        resp = self.client.post(
            url,
            {
                "aluno": "",
                "novo_aluno_nome": "Carla",
                "novo_aluno_matricula": "C001",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 30,
                "topico": "Exercícios",
                "observacoes": "",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Aluno.objects.filter(monitor=self.monitor, matricula="C001").exists())
        self.assertTrue(Atendimento.objects.filter(monitor=self.monitor, tipo=Atendimento.TIPO_INDIVIDUAL).exists())
        self.assertContains(resp, "Carla")
        self.assertContains(resp, "Exercícios")

    def test_criar_atendimento_grupo_cria_tutoria_grupo(self):
        self.login_monitor()
        url = reverse("atendimentos:criar_atendimento_grupo")
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")

        resp = self.client.post(
            url,
            {
                "data_hora": dt,
                "duracao_min": 90,
                "topico": "Aulas coletivas",
                "observacoes": "",
                "numero_participantes": 3,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        atendimento = Atendimento.objects.get(monitor=self.monitor, tipo=Atendimento.TIPO_GRUPO)
        self.assertTrue(TutoriaGrupo.objects.filter(atendimento=atendimento, numero_participantes=3).exists())
        self.assertContains(resp, "Aulas coletivas")

    def test_criar_atendimento_grupo_validacao_participantes(self):
        self.login_monitor()
        url = reverse("atendimentos:criar_atendimento_grupo")
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")

        resp = self.client.post(
            url,
            {
                "data_hora": dt,
                "duracao_min": 90,
                "topico": "Sessão inválida",
                "observacoes": "",
                "numero_participantes": 1,
            },
        )

        # Form inválido renderiza a página com erro.
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Número de participantes deve ser >= 2.", html=True)
        self.assertFalse(Atendimento.objects.filter(monitor=self.monitor, tipo=Atendimento.TIPO_GRUPO, topico="Sessão inválida").exists())

    def test_listagem_filtros_por_tipo(self):
        # Cria individual e grupo
        ind = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=40,
            topico="Individual",
            observacoes="",
        )
        Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=60,
            topico="Grupo",
            observacoes="",
        )

        self.login_monitor()
        url = reverse("atendimentos:lista_meus_atendimentos")
        resp = self.client.get(url, {"tipo": "individual"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Individual")

    def test_editar_atendimento_individual(self):
        self.login_monitor()
        ind = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=30,
            topico="Antigo",
            observacoes="",
        )

        url = reverse("atendimentos:editar_atendimento", kwargs={"pk": ind.id})
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")
        resp = self.client.post(
            url,
            {
                "aluno": self.aluno.id,
                "novo_aluno_nome": "",
                "novo_aluno_matricula": "",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 45,
                "topico": "Novo tópico",
                "observacoes": "Obs",
            },
            follow=True,
        )

        self.assertEqual(resp.status_code, 200)
        ind.refresh_from_db()
        self.assertEqual(ind.duracao_min, 45)
        self.assertEqual(ind.topico, "Novo tópico")
        self.assertContains(resp, "Novo tópico")

    def test_editar_atendimento_permissao(self):
        self.login_monitor()
        ind_outro = Atendimento.objects.create(
            monitor=self.outro_monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno_outro,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=20,
            topico="Atendimento do outro",
            observacoes="",
        )

        url = reverse("atendimentos:editar_atendimento", kwargs={"pk": ind_outro.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_editar_atendimento_grupo(self):
        self.login_monitor()
        group = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=50,
            topico="Grupo antigo",
            observacoes="",
        )
        TutoriaGrupo.objects.create(atendimento=group, numero_participantes=2)

        url = reverse("atendimentos:editar_atendimento", kwargs={"pk": group.id})
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")
        resp = self.client.post(
            url,
            {
                "data_hora": dt,
                "duracao_min": 80,
                "topico": "Grupo novo",
                "observacoes": "Obs grupo",
                "numero_participantes": 5,
            },
            follow=True,
        )

        self.assertEqual(resp.status_code, 200)
        group.refresh_from_db()
        self.assertEqual(group.duracao_min, 80)
        self.assertEqual(group.topico, "Grupo novo")
        self.assertEqual(TutoriaGrupo.objects.get(atendimento=group).numero_participantes, 5)
        self.assertContains(resp, "Grupo novo")

    def test_listagem_filtro_por_periodo_data(self):
        hoje = timezone.now()
        # Usa a data local (America/Sao_Paulo) para o filtro, já que o ORM converte
        # data_hora para o fuso ativo antes de comparar com __date__.
        hoje_local = timezone.localdate()
        ontem_local = hoje_local - timedelta(days=1)
        ontem = hoje - timedelta(days=1)
        a_hoje = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.turma.disciplina,
            data_hora=hoje,
            duracao_min=10,
            topico="Hoje",
            observacoes="",
        )
        Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.turma.disciplina,
            data_hora=ontem,
            duracao_min=10,
            topico="Ontem",
            observacoes="",
        )

        self.login_monitor()
        url = reverse("atendimentos:lista_meus_atendimentos")
        resp = self.client.get(
            url,
            {"data_inicio": hoje_local.isoformat(), "data_fim": hoje_local.isoformat()},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Hoje")
        self.assertNotContains(resp, "Ontem")

    def test_criar_atendimento_individual_validacao_sem_aluno(self):
        self.login_monitor()
        url = reverse("atendimentos:criar_atendimento_individual")
        dt = timezone.now().strftime("%Y-%m-%dT%H:%M")

        resp = self.client.post(
            url,
            {
                "aluno": "",
                "novo_aluno_nome": "",
                "novo_aluno_matricula": "",
                "novo_aluno_email": "",
                "data_hora": dt,
                "duracao_min": 30,
                "topico": "Sem aluno",
                "observacoes": "",
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Selecione um aluno ou preencha nome e matrícula para cadastrar inline.")
        self.assertFalse(Atendimento.objects.filter(monitor=self.monitor, topico="Sem aluno").exists())

    def test_excluir_atendimento(self):
        self.login_monitor()
        ind = Atendimento.objects.create(
            monitor=self.monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=self.aluno,
            disciplina=self.turma.disciplina,
            data_hora=timezone.now(),
            duracao_min=30,
            topico="Para excluir",
            observacoes="",
        )
        delete_url = reverse("atendimentos:excluir_atendimento", kwargs={"pk": ind.id})

        resp_get = self.client.get(delete_url)
        self.assertEqual(resp_get.status_code, 200)

        resp = self.client.post(delete_url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Atendimento.objects.filter(id=ind.id).exists())

    def test_alunos_frequentes_crud_cria_e_usa_busca(self):
        self.login_monitor()
        url = reverse("atendimentos:alunos_frequentes")

        resp = self.client.post(
            url,
            {"nome": "Daniela", "matricula": "D001", "email": "daniela@example.com"},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Aluno.objects.filter(monitor=self.monitor, matricula="D001").exists())

        # Busca deve retornar apenas alunos do monitor logado
        resp = self.client.get(url, {"q": "A001"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

