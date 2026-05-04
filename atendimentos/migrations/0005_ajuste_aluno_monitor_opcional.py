import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('atendimentos', '0003_monitor_usuario_fk'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='aluno',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='aluno',
            name='matricula',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='aluno',
            name='monitor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alunos', to='atendimentos.monitor'),
        ),
    ]