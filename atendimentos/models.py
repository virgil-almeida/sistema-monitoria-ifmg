import uuid as uuid_lib

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from django.utils import timezone

from accounts.models import Usuario
from curriculum.models import Disciplina, Turma


class Monitor(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        limit_choices_to={"perfil": "monitor"},
        related_name="monitores",
    )
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="monitores")
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("usuario", "turma")

    def __str__(self) -> str:
        return f"Monitor {self.usuario.username} - {self.turma}"


class Aluno(models.Model):
    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        related_name="alunos",
        null=True,
        blank=True,
    )
    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.matricula})"





class Atendimento(models.Model):
    TIPO_INDIVIDUAL = "individual"
    TIPO_GRUPO = "grupo"
    TIPO_CHOICES = [
        (TIPO_INDIVIDUAL, "Individual"),
        (TIPO_GRUPO, "Grupo"),
    ]

    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name="atendimentos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    aluno = models.ForeignKey(Aluno, on_delete=models.SET_NULL, null=True, blank=True, related_name="atendimentos")

    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, related_name="atendimentos")
    data_hora = models.DateTimeField()
    duracao_min = models.PositiveIntegerField()
    topico = models.CharField(max_length=200)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self) -> str:
        aluno_str = self.aluno.nome if self.aluno else "Grupo"
        return f"{self.tipo} - {aluno_str} - {self.disciplina} @ {self.data_hora:%Y-%m-%d}"

    def clean(self):
        # Regras básicas de consistência.
        if self.tipo == self.TIPO_INDIVIDUAL and not self.aluno:
            raise ValidationError({"aluno": "Atendimentos individuais devem ter um aluno."})
        if self.tipo == self.TIPO_GRUPO and self.aluno is not None:
            raise ValidationError({"aluno": "Atendimentos em grupo não devem ter aluno individual."})


class TutoriaGrupo(models.Model):
    atendimento = models.OneToOneField(Atendimento, on_delete=models.CASCADE, related_name="tutoria_grupo")
    numero_participantes = models.PositiveIntegerField()
    alunos = models.ManyToManyField(Aluno, blank=True, related_name="tutorias_grupo")

    class Meta:
        ordering = ["atendimento__data_hora"]

    def __str__(self) -> str:
        return f"Tutoria grupo ({self.numero_participantes}) - {self.atendimento.id}"

    def clean(self):
        if self.numero_participantes < 2:
            raise ValidationError({"numero_participantes": "Número de participantes deve ser >= 2."})


class AtendimentoSAE(models.Model):
    CATEGORIA_CHOICES = [
        ("informacoes_gerais", "Informações gerais"),
        ("pedagogia", "Pedagogia"),
        ("mediacao_disciplinar", "Mediação disciplinar"),
        ("psicologia_escolar", "Psicologia Escolar"),
        ("encaminhamentos_externos", "Encaminhamentos a instituições externas"),
        ("servico_social", "Serviço social"),
        ("napnee", "NAPNEE"),
        ("enfermidades_afastamentos", "Enfermidades, tratamentos ou afastamentos médicos"),
    ]

    data_hora = models.DateTimeField(default=timezone.now, verbose_name="Data do registro")
    estudante = models.CharField(max_length=255, verbose_name="Nome/RA/Turma")
    turma_opcional = models.CharField(max_length=100, blank=True, null=True, verbose_name="Turma (opcional)")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, verbose_name="Tipo de Registro")
    profissional = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Responsável pelo registro")
    registro = models.TextField(verbose_name="Registro")
    
    # NOVOS CAMPOS DO GOOGLE FORMS:
    eh_ata = models.BooleanField(default=False, verbose_name="Corresponde a uma ata?")
    link_ata = models.URLField(blank=True, null=True, verbose_name="Link da ata (caso seja sim)")

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Atendimento SAE"
        verbose_name_plural = "Atendimentos SAE"

    def __str__(self):
        return f"{self.estudante} - {self.get_categoria_display()}"
class SessaoMonitoria(models.Model):
    STATUS_EM_ANDAMENTO = "em_andamento"
    STATUS_FINALIZADA = "finalizada"
    STATUS_CHOICES = [
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_FINALIZADA, "Finalizada"),
    ]

    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name="sessoes")
    local = models.CharField(max_length=200)
    objetivo = models.TextField()
    inicio = models.DateTimeField(auto_now_add=True)
    fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_EM_ANDAMENTO)

    class Meta:
        ordering = ["-inicio"]

    def __str__(self) -> str:
        return f"Sessão {self.monitor} - {self.inicio:%Y-%m-%d %H:%M}"

    def duracao_minutos(self):
        ref = self.fim or timezone.now()
        return max(1, int((ref - self.inicio).total_seconds() / 60))


class ParticipanteSessao(models.Model):
    sessao = models.ForeignKey(SessaoMonitoria, on_delete=models.CASCADE, related_name="participantes")
    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=50)
    registrado_em = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)
    aluno = models.ForeignKey(
        Aluno, on_delete=models.SET_NULL, null=True, blank=True, related_name="participacoes_sessao"
    )

    class Meta:
        unique_together = [("sessao", "matricula")]
        ordering = ["registrado_em"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.matricula})"


class AtividadePreparacao(models.Model):
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name="atividades_preparacao")
    data = models.DateField()
    duracao_min = models.PositiveIntegerField()
    descricao = models.CharField(max_length=300)

    class Meta:
        ordering = ["-data"]

    def __str__(self) -> str:
        return f"Preparação {self.monitor} — {self.data:%d/%m/%Y} ({self.duracao_min}min)"


class PlanoSemana(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name="planos_semana")
    semana_inicio = models.DateField()  # sempre a segunda-feira
    planejamento = models.TextField()
    professor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="planos_semana",
        limit_choices_to={"perfil": "professor"},
    )

    class Meta:
        unique_together = [("turma", "semana_inicio")]
        ordering = ["-semana_inicio"]

    def __str__(self) -> str:
        return f"Plano {self.turma} — {self.semana_inicio:%d/%m/%Y}"
