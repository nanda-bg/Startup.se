# Generated by Django 5.0.7 on 2024-08-30 14:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresarios', '0003_metricas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documento',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresarios.empresas'),
        ),
        migrations.AlterField(
            model_name='metricas',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresarios.empresas'),
        ),
    ]
