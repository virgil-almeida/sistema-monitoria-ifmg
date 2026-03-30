from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.permissions import perfil_requerido
from curriculum.forms import DisciplinaForm, TurmaForm
from curriculum.models import Disciplina, Turma


@method_decorator(perfil_requerido("admin"), name="dispatch")
class AdminBaseMixin(LoginRequiredMixin):
    pass


class DisciplinaListView(AdminBaseMixin, ListView):
    model = Disciplina
    paginate_by = 10
    template_name = "curriculum/disciplinas_list.html"
    context_object_name = "disciplinas"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(nome__icontains=q) | Q(curso__icontains=q))
        return qs


class DisciplinaCreateView(AdminBaseMixin, CreateView):
    model = Disciplina
    form_class = DisciplinaForm
    template_name = "curriculum/disciplinas_form.html"
    success_url = reverse_lazy("curriculum:disciplinas_list")


class DisciplinaUpdateView(AdminBaseMixin, UpdateView):
    model = Disciplina
    form_class = DisciplinaForm
    template_name = "curriculum/disciplinas_form.html"
    success_url = reverse_lazy("curriculum:disciplinas_list")


class DisciplinaDeleteView(AdminBaseMixin, DeleteView):
    model = Disciplina
    template_name = "curriculum/disciplinas_confirm_delete.html"
    success_url = reverse_lazy("curriculum:disciplinas_list")


class TurmaListView(AdminBaseMixin, ListView):
    model = Turma
    paginate_by = 10
    template_name = "curriculum/turmas_list.html"
    context_object_name = "turmas"

    def get_queryset(self):
        qs = super().get_queryset().select_related("disciplina", "professor")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(disciplina__codigo__icontains=q)
                | Q(disciplina__nome__icontains=q)
                | Q(semestre__icontains=q)
                | Q(professor__username__icontains=q)
            )
        return qs


class TurmaCreateView(AdminBaseMixin, CreateView):
    model = Turma
    form_class = TurmaForm
    template_name = "curriculum/turmas_form.html"
    success_url = reverse_lazy("curriculum:turmas_list")


class TurmaUpdateView(AdminBaseMixin, UpdateView):
    model = Turma
    form_class = TurmaForm
    template_name = "curriculum/turmas_form.html"
    success_url = reverse_lazy("curriculum:turmas_list")


class TurmaDeleteView(AdminBaseMixin, DeleteView):
    model = Turma
    template_name = "curriculum/turmas_confirm_delete.html"
    success_url = reverse_lazy("curriculum:turmas_list")

