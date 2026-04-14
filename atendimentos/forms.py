from django import forms

from atendimentos.models import Aluno, Atendimento, TutoriaGrupo
from curriculum.models import Disciplina


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ("nome", "matricula", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class AtendimentoIndividualForm(forms.ModelForm):
    # Permite selecionar um aluno já cadastrado ou criar inline.
    aluno = forms.ModelChoiceField(queryset=Aluno.objects.none(), required=False)
    novo_aluno_nome = forms.CharField(max_length=200, required=False)
    novo_aluno_matricula = forms.CharField(max_length=50, required=False)
    novo_aluno_email = forms.EmailField(required=False)

    disciplina_display = forms.ModelChoiceField(
        queryset=Disciplina.objects.none(),
        required=False,
        disabled=True,
        help_text="Definido pela turma do monitor.",
    )

    class Meta:
        model = Atendimento
        fields = ("data_hora", "duracao_min", "topico", "observacoes")
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        monitor = kwargs.pop("monitor", None)
        super().__init__(*args, **kwargs)

        if monitor is not None:
            self.fields["aluno"].queryset = monitor.alunos.all()
            self.fields["disciplina_display"].queryset = Disciplina.objects.filter(id=monitor.turma.disciplina_id)
            self.fields["disciplina_display"].initial = monitor.turma.disciplina

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
    disciplina_display = forms.ModelChoiceField(
        queryset=Disciplina.objects.none(),
        required=False,
        disabled=True,
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

    def __init__(self, *args, **kwargs):
        monitor = kwargs.pop("monitor", None)
        super().__init__(*args, **kwargs)
        if monitor is not None:
            self.fields["disciplina_display"].queryset = Disciplina.objects.filter(id=monitor.turma.disciplina_id)
            self.fields["disciplina_display"].initial = monitor.turma.disciplina
            self.fields["alunos"].queryset = monitor.alunos.all().order_by("nome")

        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-control")
        self.fields["alunos"].widget.attrs.setdefault("class", "form-control")

