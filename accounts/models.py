from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    PERFIL_CHOICES = [
        ("monitor", "Monitor"),
        ("professor", "Professor"),
        ("admin", "Admin"),
    ]

    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.username} ({self.perfil})"

