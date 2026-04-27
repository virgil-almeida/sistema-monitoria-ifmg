from django.contrib import admin

from curriculum.models import Disciplina, Turma


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "curso")
    search_fields = ("codigo", "nome", "curso")
    list_filter = ("curso",)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("disciplina", "semestre", "professor")
    search_fields = ("disciplina__codigo", "disciplina__nome", "semestre", "professor__username")
    list_filter = ("semestre",)

