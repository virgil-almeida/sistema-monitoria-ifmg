from django.urls import path
from django.views.generic import RedirectView

from atendimentos.views import (
    AlunosFrequentesView,
    AtendimentoDeleteView,
    AtendimentoEditView,
    AtendimentoGrupoCreateView,
    AtendimentoIndividualCreateView,
    AtendimentoListView,
    AtividadePreparacaoDeleteView,
    AtividadePreparacaoView,
    FinalizarSessaoView,
    IniciarSessaoView,
    PainelSessaoView,
    RegistrarParticipacaoView,
    SessoesListView,
    participacao_sucesso,
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
    path("preparacao/", AtividadePreparacaoView.as_view(), name="preparacao_list"),
    path("preparacao/<int:pk>/excluir/", AtividadePreparacaoDeleteView.as_view(), name="preparacao_delete"),
    # Fluxo ao vivo
    path("sessao/iniciar/", IniciarSessaoView.as_view(), name="iniciar_sessao"),
    path("sessao/", SessoesListView.as_view(), name="minhas_sessoes"),
    path("sessao/<uuid:uuid>/painel/", PainelSessaoView.as_view(), name="painel_sessao"),
    path("sessao/<uuid:uuid>/participar/", RegistrarParticipacaoView.as_view(), name="registrar_participacao"),
    path("sessao/<uuid:uuid>/participar/ok/", participacao_sucesso, name="participacao_sucesso"),
    path("sessao/<uuid:uuid>/finalizar/", FinalizarSessaoView.as_view(), name="finalizar_sessao"),
]

