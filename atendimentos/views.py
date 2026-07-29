from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DeleteView, FormView, ListView

from core.permissions import perfil_requerido

from atendimentos.forms import (
    AlunoForm,
    AtendimentoGrupoForm,
    AtendimentoIndividualForm,
    AtendimentoSAEForm,
    AtividadePreparacaoForm,
    FinalizarSessaoForm,
    IniciarSessaoForm,
    RegistrarParticipacaoForm,
)
from atendimentos.models import (
    Aluno,
    AtividadePreparacao,
    Atendimento,
    AtendimentoSAE,
    Monitor,
    ParticipanteSessao,
    PlanoSemana,
    SessaoMonitoria,
    TutoriaGrupo,
)


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


# ── Atividades de preparação ──────────────────────────────────────────────────

@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtividadePreparacaoView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/preparacao_list.html"
    form_class = AtividadePreparacaoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitores"] = _get_monitors_or_forbidden(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        monitors = _get_monitors_or_forbidden(self.request)
        ctx["atividades"] = (
            AtividadePreparacao.objects.filter(monitor__in=monitors)
            .select_related("monitor__turma__disciplina")
        )
        messages.success(self.request, "Atividade de preparação registrada.")
        return redirect("atendimentos:preparacao_list")


@method_decorator(perfil_requerido("sae"), name="dispatch")
class AtendimentoSAEView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/atendimento_sae.html"
    form_class = AtendimentoSAEForm
    success_url = reverse_lazy("atendimentos:atendimento_sae")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        
        # Lista os atendimentos cadastrados
        atendimentos_qs = AtendimentoSAE.objects.select_related("profissional")
        
        # Filtra por nome do estudante se houver busca executada
        if q:
            atendimentos_qs = atendimentos_qs.filter(Q(estudante__icontains=q) | Q(registro__icontains=q))
            
        ctx["atendimentos"] = atendimentos_qs.order_by("-data_hora")
        ctx["q"] = q
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Atendimento SAE registrado com sucesso.")
        return redirect(self.success_url)

@method_decorator(perfil_requerido("sae"), name="dispatch")
class AtendimentoSAEDeleteView(LoginRequiredMixin, DeleteView):
    model = AtendimentoSAE
    template_name = "atendimentos/atendimento_sae_confirm_delete.html" # <- Indica o template criado
    success_url = reverse_lazy("atendimentos:atendimento_sae")
    perfil_requerido = "sae"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Atendimento do SAE excluído com sucesso!")
        return super().delete(request, *args, **kwargs)



@method_decorator(perfil_requerido("monitor"), name="dispatch")
class AtividadePreparacaoDeleteView(LoginRequiredMixin, DeleteView):
    model = AtividadePreparacao
    template_name = "atendimentos/preparacao_confirm_delete.html"
    success_url = reverse_lazy("atendimentos:preparacao_list")

    def dispatch(self, request, *args, **kwargs):
        obj = get_object_or_404(AtividadePreparacao, pk=kwargs["pk"])
        monitors = _get_monitors_or_forbidden(request)
        if not monitors.filter(id=obj.monitor_id).exists():
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)


# ── Fluxo ao vivo ─────────────────────────────────────────────────────────────

class MonitoriasAoVivoView(View):
    """Painel público (sem login) com as monitorias em andamento agora e seus locais."""

    template_name = "atendimentos/monitorias_ao_vivo.html"

    def get(self, request):
        sessoes = (
            SessaoMonitoria.objects.filter(status=SessaoMonitoria.STATUS_EM_ANDAMENTO)
            .select_related("monitor__usuario", "monitor__turma__disciplina")
            .order_by("monitor__turma__disciplina__nome", "local")
        )
        return render(request, self.template_name, {"sessoes": sessoes, "agora": timezone.now()})


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class IniciarSessaoView(LoginRequiredMixin, FormView):
    template_name = "atendimentos/sessao_iniciar.html"
    form_class = IniciarSessaoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["monitores"] = _get_monitors_or_forbidden(self.request)
        return kwargs

    def form_valid(self, form):
        cleaned = form.cleaned_data
        sessao = SessaoMonitoria.objects.create(
            monitor=cleaned["monitor"],
            local=cleaned["local"],
            objetivo=cleaned["objetivo"],
        )
        return redirect("atendimentos:painel_sessao", uuid=sessao.uuid)


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class PainelSessaoView(LoginRequiredMixin, View):
    template_name = "atendimentos/sessao_painel.html"

    def dispatch(self, request, *args, **kwargs):
        self.sessao = get_object_or_404(SessaoMonitoria, uuid=kwargs["uuid"])
        monitors = _get_monitors_or_forbidden(request)
        if not monitors.filter(id=self.sessao.monitor_id).exists():
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, uuid):
        participantes = self.sessao.participantes.all()
        url_participacao = request.build_absolute_uri(
            reverse("atendimentos:registrar_participacao", kwargs={"uuid": self.sessao.uuid})
        )
        return render(request, self.template_name, {
            "sessao": self.sessao,
            "participantes": participantes,
            "url_participacao": url_participacao,
        })


class RegistrarParticipacaoView(View):
    template_name = "atendimentos/sessao_participar.html"

    def dispatch(self, request, *args, **kwargs):
        self.sessao = get_object_or_404(SessaoMonitoria, uuid=kwargs["uuid"])
        if self.sessao.status != SessaoMonitoria.STATUS_EM_ANDAMENTO:
            return render(request, self.template_name, {"sessao": self.sessao, "encerrada": True})
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, uuid):
        form = RegistrarParticipacaoForm(sessao=self.sessao)
        return render(request, self.template_name, {"sessao": self.sessao, "form": form})

    def post(self, request, uuid):
        form = RegistrarParticipacaoForm(request.POST, sessao=self.sessao)
        if not form.is_valid():
            return render(request, self.template_name, {"sessao": self.sessao, "form": form})

        matricula = form.cleaned_data["matricula"].strip()
        nome = form.cleaned_data["nome"].strip()

        # Verifica se a matrícula já consta no cadastro de alunos
        aluno_cadastrado = Aluno.objects.filter(matricula=matricula).first()
        nome_diverge = (
            aluno_cadastrado is not None
            and aluno_cadastrado.nome.strip().lower() != nome.lower()
            and request.POST.get("confirmar") != "1"
        )
        if nome_diverge:
            return render(request, self.template_name, {
                "sessao": self.sessao,
                "form": form,
                "aluno_cadastrado": aluno_cadastrado,
            })

        nome_final = aluno_cadastrado.nome if aluno_cadastrado else nome
        ParticipanteSessao.objects.create(sessao=self.sessao, nome=nome_final, matricula=matricula)
        return redirect("atendimentos:participacao_sucesso", uuid=self.sessao.uuid)


def participacao_sucesso(request, uuid):
    sessao = get_object_or_404(SessaoMonitoria, uuid=uuid)
    return render(request, "atendimentos/sessao_participar_sucesso.html", {"sessao": sessao})


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class FinalizarSessaoView(LoginRequiredMixin, View):
    template_name = "atendimentos/sessao_finalizar.html"

    def dispatch(self, request, *args, **kwargs):
        self.sessao = get_object_or_404(SessaoMonitoria, uuid=kwargs["uuid"])
        monitors = _get_monitors_or_forbidden(request)
        if not monitors.filter(id=self.sessao.monitor_id).exists():
            return render(request, "403.html", status=403)
        if self.sessao.status == SessaoMonitoria.STATUS_FINALIZADA:
            messages.warning(request, "Esta sessão já foi finalizada.")
            return redirect("atendimentos:lista_meus_atendimentos")
        self.participantes = list(self.sessao.participantes.all())
        return super().dispatch(request, *args, **kwargs)

    def _form_kwargs(self, data=None):
        return {
            "data": data,
            "participantes": self.participantes,
            "duracao_sugerida": self.sessao.duracao_minutos(),
            "n_participantes": len(self.participantes),
        }

    def _build_context(self, form):
        participantes_e_campos = [
            (p, form[f"comentario_{p.pk}"])
            for p in self.participantes
        ]
        return {
            "sessao": self.sessao,
            "form": form,
            "participantes": self.participantes,
            "participantes_e_campos": participantes_e_campos,
        }

    def get(self, request, uuid):
        form = FinalizarSessaoForm(**self._form_kwargs())
        return render(request, self.template_name, self._build_context(form))

    def post(self, request, uuid):
        form = FinalizarSessaoForm(**self._form_kwargs(data=request.POST))
        if not form.is_valid():
            return render(request, self.template_name, self._build_context(form))
        cleaned = form.cleaned_data
        self.sessao.fim = timezone.now()
        self.sessao.status = SessaoMonitoria.STATUS_FINALIZADA
        self.sessao.save()

        monitor = self.sessao.monitor
        atendimento = Atendimento.objects.create(
            monitor=monitor,
            tipo=Atendimento.TIPO_GRUPO,
            aluno=None,
            disciplina=monitor.turma.disciplina,
            data_hora=self.sessao.inicio,
            duracao_min=cleaned["duracao_min"],
            topico=cleaned["topico"],
            observacoes=cleaned.get("observacoes", ""),
        )

        alunos_atendimento = []
        for p in self.participantes:
            comentario = cleaned.get(f"comentario_{p.pk}", "").strip()
            if comentario:
                p.comentario = comentario
                p.save(update_fields=["comentario"])
            aluno = Aluno.objects.filter(matricula=p.matricula).first()
            if aluno is not None:
                p.aluno = aluno
                p.save(update_fields=["aluno"])
                alunos_atendimento.append(aluno)

        tutoria = TutoriaGrupo.objects.create(
            atendimento=atendimento,
            numero_participantes=max(cleaned["numero_participantes"], len(self.participantes)),
        )
        tutoria.alunos.set(alunos_atendimento)

        n = len(self.participantes)
        messages.success(request, f"Monitoria finalizada! {n} participante(s) registrado(s).")
        return redirect("atendimentos:lista_meus_atendimentos")


@method_decorator(perfil_requerido("monitor"), name="dispatch")
class SessoesListView(LoginRequiredMixin, ListView):
    model = SessaoMonitoria
    template_name = "atendimentos/sessoes_list.html"
    context_object_name = "sessoes"
    paginate_by = 10

    def get_queryset(self):
        monitors = _get_monitors_or_forbidden(self.request)
        return SessaoMonitoria.objects.filter(monitor__in=monitors).select_related("monitor__turma__disciplina")


# ── Planejamento do professor — visão do monitor ───────────────────────────────

def _semana_inicio(d):
    return d - timedelta(days=d.weekday())


@perfil_requerido("monitor")
def meu_planejamento(request):
    monitors = _get_monitors_or_forbidden(request)

    # Seleciona o Monitor (turma) ativo
    monitor_id = request.GET.get("monitor")
    if monitor_id:
        monitor_sel = get_object_or_404(Monitor, pk=monitor_id, usuario=request.user, ativo=True)
    else:
        monitor_sel = monitors.first()

    # Semana selecionada
    semana_str = request.GET.get("semana")
    hoje = date.today()
    semana_atual = _semana_inicio(hoje)
    try:
        semana_selecionada = date.fromisoformat(semana_str) if semana_str else semana_atual
    except ValueError:
        semana_selecionada = semana_atual

    # Semanas: 8 passadas + atual + 2 futuras
    semanas = [semana_atual - timedelta(weeks=i) for i in range(8, -3, -1)]

    planos_existentes = {}
    plano_selecionado = None
    atendimentos_semana = []
    preparacoes_semana = []

    if monitor_sel:
        planos_existentes = {
            p.semana_inicio: p
            for p in PlanoSemana.objects.filter(turma=monitor_sel.turma)
        }
        plano_selecionado = planos_existentes.get(semana_selecionada)

        semana_fim = semana_selecionada + timedelta(days=6)
        atendimentos_semana = list(
            Atendimento.objects.filter(
                monitor=monitor_sel,
                data_hora__date__gte=semana_selecionada,
                data_hora__date__lte=semana_fim,
            ).select_related("aluno", "disciplina")
        )
        preparacoes_semana = list(
            AtividadePreparacao.objects.filter(
                monitor=monitor_sel,
                data__gte=semana_selecionada,
                data__lte=semana_fim,
            )
        )

    semanas_info = [
        {
            "inicio": s,
            "fim": s + timedelta(days=6),
            "tem_plano": s in planos_existentes,
            "ativa": s == semana_selecionada,
        }
        for s in semanas
    ]

    total_min = (
        sum(a.duracao_min for a in atendimentos_semana)
        + sum(p.duracao_min for p in preparacoes_semana)
    )

    return render(request, "atendimentos/meu_planejamento.html", {
        "monitors": monitors,
        "monitor_sel": monitor_sel,
        "semanas_info": semanas_info,
        "semana_selecionada": semana_selecionada,
        "semana_fim": semana_selecionada + timedelta(days=6),
        "plano_selecionado": plano_selecionado,
        "atendimentos_semana": atendimentos_semana,
        "preparacoes_semana": preparacoes_semana,
        "total_min": total_min,
    })