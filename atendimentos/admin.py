from django.contrib import admin

from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo, AtendimentoSAE


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ("usuario", "turma", "ativo")
    list_filter = ("ativo", "turma")
    search_fields = ("usuario__username", "turma__disciplina__codigo")


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("nome", "matricula", "monitor")
    list_filter = ("monitor__turma",)
    search_fields = ("nome", "matricula")


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "monitor", "aluno", "disciplina", "data_hora", "duracao_min")
    list_filter = ("tipo", "disciplina", "data_hora")
    search_fields = ("topico", "aluno__nome", "monitor__usuario__username")


@admin.register(TutoriaGrupo)
class TutoriaGrupoAdmin(admin.ModelAdmin):
    list_display = ("atendimento", "numero_participantes")
    search_fields = ("atendimento__topico",)

@admin.register(AtendimentoSAE)
class AtendimentoSAEAdmin(admin.ModelAdmin):
    list_display = ("estudante", "categoria", "profissional", "data_hora")
    list_filter = ("categoria", "profissional", "data_hora")
    search_fields = ("estudante", "registro", "profissional__username")