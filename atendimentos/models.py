from django.core.exceptions import ValidationError
from django.db import models

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
