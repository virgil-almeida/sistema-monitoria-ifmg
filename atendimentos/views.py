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


def _get_monitors_or_forbidden(request):
    """Retorna queryset de Monitors ativos do usuário logado. Levanta PermissionDenied se nenhum."""
    monitors = Monitor.objects.filter(usuario=request.user, ativo=True).select_related("turma__disciplina")
    if not monitors.exists():
        raise PermissionDenied("Monitor não encontrado ou inativo.")
    return monitors


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
                monitors = _get_monitors_or_forbidden(self.request)
                initial["aluno"] = Aluno.objects.get(id=aluno_id, monitor__in=monitors)
            except Aluno.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitores"] = _get_monitors_or_forbidden(self.request)
        return kwargs

    def form_valid(self, form):
        cleaned = form.cleaned_data
        monitor = cleaned["monitor"]

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

        Atendimento.objects.create(
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
        kwargs["monitores"] = _get_monitors_or_forbidden(self.request)
        return kwargs

    def form_valid(self, form):
        cleaned = form.cleaned_data
        monitor = cleaned["monitor"]

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

        tutoria = TutoriaGrupo.objects.create(
            atendimento=atendimento,
            numero_participantes=cleaned["numero_participantes"],
        )
        tutoria.alunos.set(cleaned.get("alunos") or [])

        messages.success(self.request, "Tutoria em grupo registrada com sucesso.")
        return redirect(self.get_success_url())


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoListView(LoginRequiredMixin, ListView):
    model = Atendimento
    template_name = "atendimentos/atendimentos_list.html"
    context_object_name = "atendimentos"
    paginate_by = 10

    def get_queryset(self):
        monitors = _get_monitors_or_forbidden(self.request)

        qs = (
            Atendimento.objects.filter(monitor__in=monitors)
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
        monitors = _get_monitors_or_forbidden(request)
        if not monitors.filter(id=self.atendimento.monitor_id).exists():
            return render(request, "403.html", status=403)
        self.monitors = monitors
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        if self.atendimento.tipo == Atendimento.TIPO_INDIVIDUAL:
            return AtendimentoIndividualForm
        return AtendimentoGrupoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitores"] = self.monitors

        if self.request.method in ["GET"]:
            if self.atendimento.tipo == Atendimento.TIPO_INDIVIDUAL:
                kwargs["initial"] = {
                    "monitor": self.atendimento.monitor_id,
                    "data_hora": self.atendimento.data_hora,
                    "duracao_min": self.atendimento.duracao_min,
                    "topico": self.atendimento.topico,
                    "observacoes": self.atendimento.observacoes,
                    "aluno": self.atendimento.aluno_id,
                    "novo_aluno_nome": "",
                    "novo_aluno_matricula": "",
                    "novo_aluno_email": "",
                }
            else:
                tutoria = getattr(self.atendimento, "tutoria_grupo", None)
                kwargs["initial"] = {
                    "monitor": self.atendimento.monitor_id,
                    "data_hora": self.atendimento.data_hora,
                    "duracao_min": self.atendimento.duracao_min,
                    "topico": self.atendimento.topico,
                    "observacoes": self.atendimento.observacoes,
                    "numero_participantes": tutoria.numero_participantes if tutoria else 2,
                    "alunos": tutoria.alunos.all() if tutoria else [],
                }
        return kwargs

    def form_valid(self, form):
        cleaned = form.cleaned_data
        monitor = cleaned["monitor"]

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

            self.atendimento.monitor = monitor
            self.atendimento.disciplina = monitor.turma.disciplina
            self.atendimento.aluno = aluno
            self.atendimento.data_hora = cleaned["data_hora"]
            self.atendimento.duracao_min = cleaned["duracao_min"]
            self.atendimento.topico = cleaned["topico"]
            self.atendimento.observacoes = cleaned.get("observacoes", "")
            self.atendimento.save()
        else:
            self.atendimento.monitor = monitor
            self.atendimento.disciplina = monitor.turma.disciplina
            self.atendimento.data_hora = cleaned["data_hora"]
            self.atendimento.duracao_min = cleaned["duracao_min"]
            self.atendimento.topico = cleaned["topico"]
            self.atendimento.observacoes = cleaned.get("observacoes", "")
            self.atendimento.save()

            tutoria, _ = TutoriaGrupo.objects.update_or_create(
                atendimento=self.atendimento,
                defaults={"numero_participantes": cleaned["numero_participantes"]},
            )
            tutoria.alunos.set(cleaned.get("alunos") or [])

        messages.success(self.request, "Atendimento atualizado com sucesso.")
        return redirect(self.get_success_url())


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtendimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Atendimento
    template_name = "atendimentos/atendimento_confirm_delete.html"
    success_url = reverse_lazy("atendimentos:lista_meus_atendimentos")

    def dispatch(self, request, *args, **kwargs):
        self.atendimento = get_object_or_404(Atendimento, pk=kwargs["pk"])
        monitors = _get_monitors_or_forbidden(request)
        if not monitors.filter(id=self.atendimento.monitor_id).exists():
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AlunosFrequentesView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/alunos_frequentes.html"
    form_class = AlunoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitores"] = _get_monitors_or_forbidden(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        monitors = _get_monitors_or_forbidden(self.request)
        q = self.request.GET.get("q", "").strip()
        alunos_qs = Aluno.objects.filter(monitor__in=monitors)
        if q:
            alunos_qs = alunos_qs.filter(Q(nome__icontains=q) | Q(matricula__icontains=q))
        ctx["alunos"] = alunos_qs.order_by("nome")
        ctx["q"] = q
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Aluno cadastrado com sucesso.")
        return redirect("atendimentos:alunos_frequentes")
