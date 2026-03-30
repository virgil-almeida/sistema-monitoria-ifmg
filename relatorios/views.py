import base64
import io
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncWeek
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from core.permissions import perfil_requerido
from curriculum.models import Disciplina
from atendimentos.forms import AlunoForm
from atendimentos.models import Aluno, Atendimento, Monitor, TutoriaGrupo


def _get_professor_monitorias(professor):
    turmas = professor.turmas_como_professor.all()
    monitores = Monitor.objects.filter(turma__in=turmas, ativo=True).select_related("turma", "turma__disciplina", "usuario")
    return turmas, monitores


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@method_decorator(perfil_requerido("professor"), name="dispatch")
def dashboard_professor(request):
    _, monitores = _get_professor_monitorias(request.user)
    atendimentos_qs = Atendimento.objects.filter(monitor__in=monitores).select_related("disciplina", "aluno", "monitor")

    now = timezone.now()
    start_month = date(now.year, now.month, 1)
    end_month = (start_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    atendimentos_mes = atendimentos_qs.filter(data_hora__date__gte=start_month, data_hora__date__lte=end_month)

    total_mes = atendimentos_mes.count()

    # Semanal (Chart.js): usa TruncWeek e pega alguns pontos.
    weekly = (
        atendimentos_mes.annotate(week=TruncWeek("data_hora"))
        .values("week")
        .annotate(total=Count("id"))
        .order_by("week")
    )
    labels = [w["week"].strftime("%d/%m") for w in weekly]
    data = [w["total"] for w in weekly]

    # Horas por monitor
    horas_por_monitor = (
        atendimentos_mes.values("monitor__id", "monitor__usuario__username")
        .annotate(total_horas=Sum("duracao_min"))
        .order_by("-total_horas")[:10]
    )
    # Conversão min -> horas para exibição
    monitores_cards = [
        {"username": h["monitor__usuario__username"], "horas": float(h["total_horas"] or 0) / 60.0}
        for h in horas_por_monitor
    ]

    # Alerta: alunos com mais atendimentos (individuais)
    top_alunos = (
        atendimentos_mes.filter(tipo=Atendimento.TIPO_INDIVIDUAL, aluno__isnull=False)
        .values("aluno__id", "aluno__nome", "aluno__matricula")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    return render(
        request,
        "relatorios/dashboard_professor.html",
        {
            "total_mes": total_mes,
            "chart_labels": labels,
            "chart_data": data,
            "monitores_cards": monitores_cards,
            "top_alunos": top_alunos,
        },
    )


@method_decorator(perfil_requerido("professor"), name="dispatch")
def historico_aluno(request):
    _, monitores = _get_professor_monitorias(request.user)
    alunos_qs = Aluno.objects.filter(monitor__in=monitores)

    q = request.GET.get("q", "").strip()
    aluno_selecionado = None
    atendimentos = None
    total_atendimentos = 0

    if q:
        aluno_selecionado = alunos_qs.filter(Q(nome__icontains=q) | Q(matricula__icontains=q)).first()
        if aluno_selecionado:
            atendimentos = (
                Atendimento.objects.filter(monitor__in=monitores, aluno=aluno_selecionado)
                .select_related("monitor__usuario", "disciplina", "aluno")
                .order_by("data_hora")
            )
            total_atendimentos = atendimentos.count()

    return render(
        request,
        "relatorios/historico_aluno.html",
        {
            "q": q,
            "aluno_selecionado": aluno_selecionado,
            "atendimentos": atendimentos,
            "total_atendimentos": total_atendimentos,
        },
    )


@method_decorator(perfil_requerido("professor"), name="dispatch")
def ranking_dificuldades(request):
    _, monitores = _get_professor_monitorias(request.user)

    periodo_tipo = request.GET.get("periodo_tipo", "mes")
    disciplina_id = request.GET.get("disciplina", "")
    disciplina = None
    if disciplina_id:
        disciplina = Disciplina.objects.filter(id=disciplina_id).first()

    today = timezone.now().date()
    ano = int(request.GET.get("ano", today.year))
    # semestre: 1 ou 2
    semestre_num = int(request.GET.get("semestre", "1"))
    mes = int(request.GET.get("mes", today.month))

    if periodo_tipo == "semestre":
        if semestre_num == 1:
            inicio = date(ano, 1, 1)
            fim = date(ano, 6, 30)
        else:
            inicio = date(ano, 7, 1)
            fim = date(ano, 12, 31)
    else:
        inicio = date(ano, mes, 1)
        fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    qs = Atendimento.objects.filter(
        monitor__in=monitores,
        tipo=Atendimento.TIPO_INDIVIDUAL,
        data_hora__date__gte=inicio,
        data_hora__date__lte=fim,
        aluno__isnull=False,
    )
    if disciplina:
        qs = qs.filter(disciplina=disciplina)

    ranking = (
        qs.values("aluno__id", "aluno__nome", "aluno__matricula")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    return render(
        request,
        "relatorios/ranking_dificuldades.html",
        {
            "periodo_tipo": periodo_tipo,
            "disciplina": disciplina,
            "disciplinas": Disciplina.objects.all(),
            "ranking": ranking,
            "inicio": inicio,
            "fim": fim,
            "ano": ano,
            "mes": mes,
            "semestre": semestre_num,
        },
    )


@method_decorator(perfil_requerido("professor"), name="dispatch")
def relatorio_avancado(request):
    _, monitores = _get_professor_monitorias(request.user)
    qs = Atendimento.objects.filter(monitor__in=monitores).select_related("aluno", "disciplina", "monitor__usuario")

    periodo_inicio = _parse_date(request.GET.get("data_inicio", ""))
    periodo_fim = _parse_date(request.GET.get("data_fim", ""))
    monitor_id = request.GET.get("monitor", "").strip()
    disciplina_id = request.GET.get("disciplina", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    if periodo_inicio:
        qs = qs.filter(data_hora__date__gte=periodo_inicio)
    if periodo_fim:
        qs = qs.filter(data_hora__date__lte=periodo_fim)

    if monitor_id:
        qs = qs.filter(monitor__id=monitor_id)
    if disciplina_id:
        qs = qs.filter(disciplina__id=disciplina_id)
    if tipo in [Atendimento.TIPO_INDIVIDUAL, Atendimento.TIPO_GRUPO]:
        qs = qs.filter(tipo=tipo)

    # Paginação simples (ListView não usado para manter controle)
    page_size = 10
    page = int(request.GET.get("page", "1"))
    total_count = qs.count()
    total_horas_min = qs.aggregate(total=Sum("duracao_min"))["total"] or 0

    start = (page - 1) * page_size
    end = start + page_size
    attend_pag = list(qs.order_by("-data_hora")[start:end])

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return render(
        request,
        "relatorios/relatorio_avancado.html",
        {
            "qs_total": total_count,
            "qs_total_horas": float(total_horas_min) / 60.0,
            "attend_pag": attend_pag,
            "page": page,
            "total_pages": total_pages,
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
            "monitor_id": monitor_id,
            "disciplina_id": disciplina_id,
            "tipo": tipo,
            "monitores": monitores,
            "disciplinas": Disciplina.objects.all(),
        },
    )


def _base64_logo_ifmg():
    # Placeholder simples (1x1 px) para cumprir o cabeçalho.
    # O ideal é substituir pelo arquivo real em `static/img/logo-ifmg.png`.
    one_px_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+9VJkAAAAASUVORK5CYII="
    )
    return base64.b64decode(one_px_png_b64)


@method_decorator(perfil_requerido("professor"), name="dispatch")
def exportar_pdf(request):
    # Reaproveita exatamente os filtros da tela.
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_monitoria.pdf"'

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfgen import canvas

    _, monitores = _get_professor_monitorias(request.user)
    qs = Atendimento.objects.filter(monitor__in=monitores).select_related("aluno", "disciplina", "monitor__usuario")

    periodo_inicio = _parse_date(request.GET.get("data_inicio", ""))
    periodo_fim = _parse_date(request.GET.get("data_fim", ""))
    monitor_id = request.GET.get("monitor", "").strip()
    disciplina_id = request.GET.get("disciplina", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    if periodo_inicio:
        qs = qs.filter(data_hora__date__gte=periodo_inicio)
    if periodo_fim:
        qs = qs.filter(data_hora__date__lte=periodo_fim)
    if monitor_id:
        qs = qs.filter(monitor__id=monitor_id)
    if disciplina_id:
        qs = qs.filter(disciplina__id=disciplina_id)
    if tipo in [Atendimento.TIPO_INDIVIDUAL, Atendimento.TIPO_GRUPO]:
        qs = qs.filter(tipo=tipo)

    qs = qs.order_by("-data_hora")
    total_count = qs.count()
    total_min = qs.aggregate(total=Sum("duracao_min"))["total"] or 0
    total_horas = float(total_min) / 60.0
    monitor_label = "Todos"
    if monitor_id:
        monitor_label = str(Monitor.objects.filter(id=monitor_id).select_related("usuario").first().usuario.username)  # type: ignore[union-attr]

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(response, pagesize=A4)
    elems = []

    # Cabeçalho com "logo" placeholder.
    logo_bytes = _base64_logo_ifmg()
    logo = Image(io.BytesIO(logo_bytes), width=60, height=30)
    elems.append(logo)
    elems.append(Paragraph("IFMG - Sistema de Monitoria", styles["Title"]))
    elems.append(Spacer(1, 12))

    elems.append(
        Paragraph(
            f"Período: {periodo_inicio or '—'} até {periodo_fim or '—'}<br/>"
            f"Tipo: {tipo or 'Todos'}<br/>"
            f"Monitor: {monitor_label}<br/>"
            f"Total de atendimentos: {total_count}<br/>"
            f"Total de horas: {total_horas:.2f}",
            styles["Normal"],
        )
    )

    elems.append(Spacer(1, 12))

    data = [["Data/Hora", "Tipo", "Monitor", "Aluno", "Disciplina", "Duração (min)", "Tópico"]]
    for a in qs[:200]:  # evita PDF gigantescos em teste
        data.append(
            [
                a.data_hora.strftime("%d/%m/%Y %H:%M"),
                "Individual" if a.tipo == Atendimento.TIPO_INDIVIDUAL else "Grupo",
                a.monitor.usuario.username,
                a.aluno.nome if a.aluno else "-",
                a.disciplina.codigo,
                str(a.duracao_min),
                a.topico,
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    elems.append(table)

    doc.build(elems)
    return response

