from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DeleteView, FormView, ListView

from core.permissions import perfil_requerido
from atendimentos.forms import (
    AlunoForm,
    AtendimentoGrupoForm,
    AtendimentoIndividualForm,
)
from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo


def _get_monitor_or_forbidden(request) -> Monitor:
    try:
        monitor = request.user.monitor
    except Monitor.DoesNotExist:
        raise PermissionDenied("Monitor não encontrado.")
    if not monitor.ativo:
        raise PermissionDenied("Monitor inativo.")
    return monitor


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoIndividualCreateView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/atendimento_individual_form.html"
    form_class = AtendimentoIndividualForm
    success_url = reverse_lazy("atendimentos:lista_meus_atendimentos")

    def get_initial(self):
        initial = super().get_initial()
        aluno_id = self.request.GET.get("aluno")
        if aluno_id:
            try:
                initial["aluno"] = Aluno.objects.get(id=aluno_id, monitor=_get_monitor_or_forbidden(self.request))
            except Aluno.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitor"] = _get_monitor_or_forbidden(self.request)
        return kwargs

    def form_valid(self, form):
        monitor = _get_monitor_or_forbidden(self.request)
        cleaned = form.cleaned_data

        aluno = cleaned.get("aluno")
        novo_nome = cleaned.get("novo_aluno_nome", "").strip()
        novo_matricula = cleaned.get("novo_aluno_matricula", "").strip()
        novo_email = cleaned.get("novo_aluno_email", "").strip()

        if aluno is None:
            aluno = Aluno.objects.create(
                monitor=monitor,
                nome=novo_nome,
                matricula=novo_matricula,
                email=novo_email or None,
            )

        atendimento = Atendimento.objects.create(
            monitor=monitor,
            tipo=Atendimento.TIPO_INDIVIDUAL,
            aluno=aluno,
            disciplina=monitor.turma.disciplina,
            data_hora=cleaned["data_hora"],
            duracao_min=cleaned["duracao_min"],
            topico=cleaned["topico"],
            observacoes=cleaned.get("observacoes", ""),
        )

        messages.success(self.request, f"Atendimento registrado para {aluno.nome}.")
        return redirect(self.get_success_url())


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoGrupoCreateView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/atendimento_grupo_form.html"
    form_class = AtendimentoGrupoForm
    success_url = reverse_lazy("atendimentos:lista_meus_atendimentos")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitor"] = _get_monitor_or_forbidden(self.request)
        return kwargs

    def form_valid(self, form):
        monitor = _get_monitor_or_forbidden(self.request)
        cleaned = form.cleaned_data

        atendimento = Atendimento.objects.create(
            monitor=monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=monitor.turma.disciplina,
            data_hora=cleaned["data_hora"],
            duracao_min=cleaned["duracao_min"],
            topico=cleaned["topico"],
            observacoes=cleaned.get("observacoes", ""),
        )

        TutoriaGrupo.objects.create(
            atendimento=atendimento,
            numero_participantes=cleaned["numero_participantes"],
        )

        messages.success(self.request, "Tutoria em grupo registrada com sucesso.")
        return redirect(self.get_success_url())


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoListView(LoginRequiredMixin, ListView):
    model = Atendimento
    template_name = "atendimentos/atendimentos_list.html"
    context_object_name = "atendimentos"
    paginate_by = 10

    def get_queryset(self):
        monitor = _get_monitor_or_forbidden(self.request)

        qs = (
            Atendimento.objects.filter(monitor=monitor)
            .select_related("aluno", "disciplina")
            .order_by("-data_hora")
        )

        tipo = self.request.GET.get("tipo", "").strip()
        if tipo in [Atendimento.TIPO_INDIVIDUAL, Atendimento.TIPO_GRUPO]:
            qs = qs.filter(tipo=tipo)

        data_inicio = self.request.GET.get("data_inicio", "").strip()
        data_fim = self.request.GET.get("data_fim", "").strip()
        if data_inicio:
            qs = qs.filter(data_hora__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_hora__date__lte=data_fim)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_filtro"] = self.request.GET.get("tipo", "")
        ctx["data_inicio"] = self.request.GET.get("data_inicio", "")
        ctx["data_fim"] = self.request.GET.get("data_fim", "")
        return ctx


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoEditView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/atendimento_edit.html"
    success_url = reverse_lazy("atendimentos:lista_meus_atendimentos")

    def dispatch(self, request, *args, **kwargs):
        self.atendimento = get_object_or_404(Atendimento, pk=kwargs["pk"])
        monitor = _get_monitor_or_forbidden(request)
        if self.atendimento.monitor_id != monitor.id:
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        if self.atendimento.tipo == Atendimento.TIPO_INDIVIDUAL:
            return AtendimentoIndividualForm
        return AtendimentoGrupoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitor"] = _get_monitor_or_forbidden(self.request)

        if self.request.method in ["GET"]:
            if self.atendimento.tipo == Atendimento.TIPO_INDIVIDUAL:
                kwargs["initial"] = {
                    "data_hora": self.atendimento.data_hora,
                    "duracao_min": self.atendimento.duracao_min,
                    "topico": self.atendimento.topico,
                    "observacoes": self.atendimento.observacoes,
                    "aluno": self.atendimento.aluno_id,
                    "novo_aluno_nome": "",
                    "novo_aluno_matricula": "",
                    "novo_aluno_email": "",
                    "disciplina_display": self.atendimento.disciplina_id,
                }
            else:
                kwargs["initial"] = {
                    "data_hora": self.atendimento.data_hora,
                    "duracao_min": self.atendimento.duracao_min,
                    "topico": self.atendimento.topico,
                    "observacoes": self.atendimento.observacoes,
                    "numero_participantes": getattr(self.atendimento.tutoria_grupo, "numero_participantes", 2),
                    "disciplina_display": self.atendimento.disciplina_id,
                }
        return kwargs

    def form_valid(self, form):
        monitor = _get_monitor_or_forbidden(self.request)
        cleaned = form.cleaned_data

        if self.atendimento.tipo == Atendimento.TIPO_INDIVIDUAL:
            aluno = cleaned.get("aluno")
            if aluno is None:
                novo_nome = cleaned.get("novo_aluno_nome", "").strip()
                novo_matricula = cleaned.get("novo_aluno_matricula", "").strip()
                novo_email = cleaned.get("novo_aluno_email", "").strip()
                aluno = Aluno.objects.create(
                    monitor=monitor,
                    nome=novo_nome,
                    matricula=novo_matricula,
                    email=novo_email or None,
                )

            self.atendimento.aluno = aluno
            self.atendimento.data_hora = cleaned["data_hora"]
            self.atendimento.duracao_min = cleaned["duracao_min"]
            self.atendimento.topico = cleaned["topico"]
            self.atendimento.observacoes = cleaned.get("observacoes", "")
            self.atendimento.save()
        else:
            self.atendimento.data_hora = cleaned["data_hora"]
            self.atendimento.duracao_min = cleaned["duracao_min"]
            self.atendimento.topico = cleaned["topico"]
            self.atendimento.observacoes = cleaned.get("observacoes", "")
            self.atendimento.save()

            TutoriaGrupo.objects.update_or_create(
                atendimento=self.atendimento,
                defaults={"numero_participantes": cleaned["numero_participantes"]},
            )

        messages.success(self.request, "Atendimento atualizado com sucesso.")
        return redirect(self.get_success_url())


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Atendimento
    template_name = "atendimentos/atendimento_confirm_delete.html"
    success_url = reverse_lazy("atendimentos:lista_meus_atendimentos")

    def dispatch(self, request, *args, **kwargs):
        self.atendimento = get_object_or_404(Atendimento, pk=kwargs["pk"])
        monitor = _get_monitor_or_forbidden(request)
        if self.atendimento.monitor_id != monitor.id:
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AlunosFrequentesView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/alunos_frequentes.html"
    form_class = AlunoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        monitor = _get_monitor_or_forbidden(self.request)
        q = self.request.GET.get("q", "").strip()
        alunos_qs = monitor.alunos.all()
        if q:
            alunos_qs = alunos_qs.filter(Q(nome__icontains=q) | Q(matricula__icontains=q))
        ctx["alunos"] = alunos_qs.order_by("nome")
        ctx["q"] = q
        return ctx

    def form_valid(self, form):
        monitor = _get_monitor_or_forbidden(self.request)
        aluno = form.save(commit=False)
        aluno.monitor = monitor
        aluno.save()
        messages.success(self.request, "Aluno cadastrado com sucesso.")
        return redirect("atendimentos:alunos_frequentes")

