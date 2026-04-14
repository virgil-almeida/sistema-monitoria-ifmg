from django.urls import path
from django.views.generic import RedirectView

from atendimentos.views import (
    AlunosFrequentesView,
    AtendimentoDeleteView,
    AtendimentoEditView,
    AtendimentoGrupoCreateView,
    AtendimentoIndividualCreateView,
    AtendimentoListView,
)

app_name = "atendimentos"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="atendimentos:lista_meus_atendimentos", permanent=False)),
    path("meus/", AtendimentoListView.as_view(), name="lista_meus_atendimentos"),
    path("individual/novo/", AtendimentoIndividualCreateView.as_view(), name="criar_atendimento_individual"),
    path("grupo/novo/", AtendimentoGrupoCreateView.as_view(), name="criar_atendimento_grupo"),
    path("atendimento/<int:pk>/editar/", AtendimentoEditView.as_view(), name="editar_atendimento"),
    path("atendimento/<int:pk>/excluir/", AtendimentoDeleteView.as_view(), name="excluir_atendimento"),
    path("alunos/", AlunosFrequentesView.as_view(), name="alunos_frequentes"),
]

