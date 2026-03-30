from django import forms

from atendimentos.models import Monitor
from curriculum.models import Disciplina, Turma


class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ("nome", "codigo", "curso")


class TurmaForm(forms.ModelForm):
    monitores = forms.ModelMultipleChoiceField(
        queryset=Monitor.objects.all(),
        required=False,
        help_text="Selecione os monitores que ficarão vinculados a esta turma.",
    )

    class Meta:
        model = Turma
        fields = ("disciplina", "semestre", "professor", "monitores")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mantém apenas monitores criados, independente de ativo/inativo.
        self.fields["monitores"].queryset = Monitor.objects.select_related("turma")

    def save(self, commit=True):
        turma = super().save(commit=False)
        if commit:
            turma.save()
            for monitor in self.cleaned_data.get("monitores", []):
                monitor.turma = turma
                monitor.ativo = True
                monitor.save()
        return turma

