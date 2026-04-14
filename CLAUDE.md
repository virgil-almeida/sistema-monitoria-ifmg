# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Sistema de controle de monitoria para o IFMG Betim — a Django web app for managing peer-tutoring sessions between monitors (student tutors) and their students, with professor oversight and reporting.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in SECRET_KEY and DB_* vars
python manage.py migrate
python manage.py createsuperuser   # then set perfil='admin' in Django Admin

# Development
python manage.py runserver

# Tests
python manage.py test                                        # all tests
python manage.py test atendimentos                           # single app
python manage.py test atendimentos.tests.AtendimentosSprint2Tests.test_criar_atendimento_individual_com_aluno_existente  # single test

# Coverage (mirrors CI)
python -m coverage run --source=atendimentos -m django test -v 2
python -m coverage report --fail-under=70 -m

# Production
python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=monitoria_ifmg.production_settings gunicorn monitoria_ifmg.wsgi
```

## Architecture

### User roles and access control

Three roles live on the custom `Usuario` model (accounts/models.py): `monitor`, `professor`, `admin`. Views are gated by the `@perfil_requerido(role)` decorator (core/permissions.py), which returns 403 on mismatch. `PerfilAtivoMiddleware` (core/middleware.py) enforces active profile state on every request.

### App responsibilities

| App | Purpose |
|-----|---------|
| `accounts` | Login, logout, registration; custom `Usuario` model |
| `core` | Home routing, permission decorator, middleware |
| `curriculum` | `Disciplina` + `Turma` CRUD (admin only) |
| `atendimentos` | Core domain — `Monitor`, `Aluno`, `Atendimento`, `TutoriaGrupo` models; individual and group session CRUD |
| `relatorios` | Professor dashboard, historical lookup, difficulty ranking, PDF export (ReportLab) |

### Data model relationships

```
Disciplina ──< Turma >── professor (Usuario)
                │
                └──< Monitor >── usuario (Usuario, perfil=monitor)
                                │
                                └──< Aluno
                                │
                                └──< Atendimento ──< TutoriaGrupo (grupo only)
```

`Atendimento.tipo` is either `individual` or `grupo`; group sessions require `TutoriaGrupo.numero_participantes >= 2`.

### Settings

| Module | When used |
|--------|-----------|
| `monitoria_ifmg.settings` | Default (dev) — SQLite, DEBUG=True |
| `monitoria_ifmg.test_settings` | Tests — in-memory SQLite |
| `monitoria_ifmg.production_settings` | Prod — DEBUG=False, STATIC_ROOT, PostgreSQL |

Environment variables are loaded via `python-decouple` from `.env`. Required vars: `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR: Python 3.12, runs the full test suite, enforces ≥70% coverage on the `atendimentos` source.

### Frontend

Templates use AdminLTE 3 / Bootstrap; `base.html` is the shared layout. Charts use Chart.js. PDF reports are generated server-side with ReportLab (max 200 rows per export).
