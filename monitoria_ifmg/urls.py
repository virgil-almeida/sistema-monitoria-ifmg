from django.contrib import admin
from django.urls import include, path

from core.views import home


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("curriculum/", include("curriculum.urls")),
    path("atendimentos/", include("atendimentos.urls")),
    path("relatorios/", include("relatorios.urls")),
]

