import random
from django.template.context_processors import request
from django import forms

from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo
from curriculum.models import Disciplina


class MonitorChoiceField(forms.ModelChoiceField):
    """Exibe a turma (disciplina + semestre) como label, sem repetir o username."""

    def label_from_instance(self, obj):
        return str(obj.turma)  # ex: "ALG101 - Algoritmos (2026/1)"


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ("monitor", "nome", "matricula", "email")

    def __init__(self, *args, monitores=None, **kwargs):
        super().__init__(*args, **kwargs)
        mon_field = MonitorChoiceField(
            queryset=Monitor.objects.none(),
            label="Disciplina/Turma",
            required=False,
        )
        self.fields["monitor"] = mon_field

        if monitores is not None:
            qs = monitores if hasattr(monitores, "filter") else Monitor.objects.filter(pk__in=monitores)
            self.fields["monitor"].queryset = qs
            if qs.count() == 1:
                self.fields["monitor"].initial = qs.first()
                self.fields["monitor"].widget = forms.HiddenInput()

        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault("class", "form-control")


class AtendimentoIndividualForm(forms.ModelForm):
    monitor = MonitorChoiceField(
        queryset=Monitor.objects.none(),
        label="Disciplina/Turma",
    )
    aluno = forms.ModelChoiceField(queryset=Aluno.objects.none(), required=False)
    novo_aluno_nome = forms.CharField(max_length=200, required=False)
    novo_aluno_matricula = forms.CharField(max_length=50, required=False)
    novo_aluno_email = forms.EmailField(required=False)

    class Meta:
        model = Atendimento
        fields = ("monitor", "data_hora", "duracao_min", "topico", "observacoes")
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, monitores=None, **kwargs):
        super().__init__(*args, **kwargs)

        if monitores is not None:
            self.fields["monitor"].queryset = monitores
            self.fields["aluno"].queryset = Aluno.objects.filter(monitor__in=monitores)

        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        aluno = cleaned.get("aluno")
        novo_nome = cleaned.get("novo_aluno_nome", "").strip()
        novo_matricula = cleaned.get("novo_aluno_matricula", "").strip()

        if aluno is None:
            if not novo_nome or not novo_matricula:
                raise forms.ValidationError("Selecione um aluno ou preencha nome e matrícula para cadastrar inline.")
        return cleaned


class AtendimentoGrupoForm(forms.Form):
    monitor = MonitorChoiceField(
        queryset=Monitor.objects.none(),
        label="Disciplina/Turma",
    )
    data_hora = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    duracao_min = forms.IntegerField(min_value=1)
    topico = forms.CharField(max_length=200)
    observacoes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    numero_participantes = forms.IntegerField(
        help_text="Total de participantes (incluindo os não cadastrados).",
    )
    alunos = forms.ModelMultipleChoiceField(
        queryset=Aluno.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": "8"}),
        label="Alunos presentes",
        help_text="Segure Ctrl (ou Cmd no Mac) para selecionar mais de um.",
    )

    def clean(self):
        cleaned = super().clean()
        numero = cleaned.get("numero_participantes")
        alunos = cleaned.get("alunos") or []
        if numero is not None and numero < 2:
            raise forms.ValidationError("Número de participantes deve ser >= 2.")
        if numero is not None and len(alunos) > numero:
            raise forms.ValidationError(
                "O número de participantes não pode ser menor que a quantidade de alunos selecionados."
            )
        return cleaned

    def __init__(self, *args, monitores=None, **kwargs):
        super().__init__(*args, **kwargs)
        if monitores is not None:
            self.fields["monitor"].queryset = monitores
            self.fields["alunos"].queryset = Aluno.objects.filter(monitor__in=monitores).order_by("nome")

        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-control")
        self.fields["alunos"].widget.attrs.setdefault("class", "form-control")
