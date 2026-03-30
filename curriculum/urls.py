from django.urls import path

from curriculum import views

app_name = "curriculum"

urlpatterns = [
    path("disciplinas/", views.DisciplinaListView.as_view(), name="disciplinas_list"),
    path("disciplinas/novo/", views.DisciplinaCreateView.as_view(), name="disciplinas_create"),
    path("disciplinas/<int:pk>/editar/", views.DisciplinaUpdateView.as_view(), name="disciplinas_update"),
    path(
        "disciplinas/<int:pk>/excluir/",
        views.DisciplinaDeleteView.as_view(),
        name="disciplinas_delete",
    ),
    path("turmas/", views.TurmaListView.as_view(), name="turmas_list"),
    path("turmas/novo/", views.TurmaCreateView.as_view(), name="turmas_create"),
    path("turmas/<int:pk>/editar/", views.TurmaUpdateView.as_view(), name="turmas_update"),
    path("turmas/<int:pk>/excluir/", views.TurmaDeleteView.as_view(), name="turmas_delete"),
]

