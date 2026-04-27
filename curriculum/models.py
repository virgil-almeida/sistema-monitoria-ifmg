from django.db import models

from accounts.models import Usuario


class Disciplina(models.Model):
    nome = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50)
    curso = models.CharField(max_length=200)

    class Meta:
        unique_together = ("codigo", "curso")
        ordering = ["curso", "codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"


class Turma(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="turmas")
    semestre = models.CharField(max_length=20)
    professor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="turmas_como_professor",
        limit_choices_to={"perfil": "professor"},
    )

    class Meta:
        unique_together = ("disciplina", "semestre")
        ordering = ["semestre"]

    def __str__(self) -> str:
        return f"{self.disciplina} ({self.semestre})"

