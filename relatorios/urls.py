from django.urls import path

from relatorios.views import (
    dashboard_professor,
    exportar_pdf,
    historico_aluno,
    planejamento_monitoria,
    ranking_dificuldades,
    relatorio_avancado,
    relatorio_planejamento,
)

app_name = "relatorios"

urlpatterns = [
    path("", dashboard_professor, name="dashboard_professor"),
    path("historico/", historico_aluno, name="historico_aluno"),
    path("ranking/", ranking_dificuldades, name="ranking_dificuldades"),
    path("relatorio/", relatorio_avancado, name="relatorio_avancado"),
    path("relatorio/pdf/", exportar_pdf, name="exportar_pdf"),
    path("planejamento/", planejamento_monitoria, name="planejamento_monitoria"),
    path("planejamento/relatorio/", relatorio_planejamento, name="relatorio_planejamento"),
]
