# Sistema de Monitoria IFMG

Sistema de controle de monitoria — IFMG Betim

Stack: `Django` + `PostgreSQL` + `AdminLTE 3` + relatórios (PDF).

## Requisitos

- Python 3.11+ (testado com 3.12)
- PostgreSQL

## Instalação local

1. Criar ambiente virtual:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Instalar dependências:
   - `pip install -r requirements.txt`
3. Configurar variáveis de ambiente:
   - copie `.env.example` para `.env`
   - ajuste `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `SECRET_KEY`
4. Rodar migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
5. Criar usuário admin (Django):
   - `python manage.py createsuperuser`
   - depois defina o campo `perfil` do usuário para `admin` no `Django Admin`
6. Rodar o servidor:
   - `python manage.py runserver`

## URLs principais

- `/accounts/login/` - login
- `/admin/` - Django Admin
- Para fluxo do sistema:
  - Monitor: menu “Meus atendimentos”, “Registrar individual/grupo”, “Meus alunos”
  - Professor: “Dashboard”, “Histórico”, “Dificuldades”, “Relatórios”
  - Admin: “Disciplinas” e “Turmas” (CRUD custom + AdminLTE)

## Manual básico do usuário

### Monitor

1. Logar no sistema.
2. (Opcional) Cadastrar alunos frequentes em **Meus alunos**.
3. Registrar um atendimento:
   - **Registrar individual**: selecione um aluno cadastrado ou crie inline.
   - **Registrar grupo**: registre a sessão coletiva e o número de participantes (>= 2).
4. Acompanhar/editar:
   - **Meus atendimentos**: listar, filtrar por tipo e período, editar e excluir seus próprios registros.

### Professor orientador

1. Logar no sistema.
2. Visão geral:
   - **Dashboard**: cards do mês, gráfico por semana e alerta de alunos com muitos atendimentos.
3. Relatórios:
   - **Histórico**: busque aluno por nome ou matrícula e veja a cronologia.
   - **Dificuldades**: ranking top 10 com filtros por disciplina e período (mês/semestre).
   - **Relatórios**: filtros avançados + exportação em PDF (mesmos filtros da tela).

## Diagrama simplificado do banco (relacionamentos)

```mermaid
erDiagram
  Usuario {
    id
    username
    perfil
  }
  Disciplina {
    id
    codigo
    nome
    curso
  }
  Turma {
    id
    semestre
  }
  Monitor {
    id
    ativo
  }
  Aluno {
    id
    nome
    matricula
    email
  }
  Atendimento {
    id
    tipo
    data_hora
    duracao_min
    topico
  }
  TutoriaGrupo {
    id
    numero_participantes
  }

  Usuario ||--o{ Turma : professor
  Disciplina ||--o{ Turma : possui
  Usuario ||--o| Monitor : usuario
  Turma ||--o{ Monitor : turma
  Monitor ||--o{ Aluno : cadastra
  Monitor ||--o{ Atendimento : registra
  Disciplina ||--o{ Atendimento : inclui
  Aluno ||--o{ Atendimento : aluno
  Atendimento ||--|| TutoriaGrupo : grupo
```

## Testes e CI

O repositório inclui uma pipeline de CI (GitHub Actions) para rodar testes e checar cobertura via `coverage.py`.
Se você quiser executar localmente:

- `python manage.py test`

## Deploy (produção)

1. Configure variáveis de ambiente no servidor (obrigatório):
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS` (ex.: `seu-dominio.com, www.seu-dominio.com`)
   - variáveis do Postgres (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)
2. Use `DJANGO_SETTINGS_MODULE=monitoria_ifmg.production_settings`.
3. Colete arquivos estáticos:
   - `python manage.py collectstatic --noinput`
4. Rode migrations:
   - `python manage.py migrate`
5. Inicie o servidor WSGI (ex.: Gunicorn/Nginx conforme sua infra).

