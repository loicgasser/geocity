# Generated by Django 2.2.6 on 2020-05-19 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0012_permitrequestvalidation'),
    ]

    operations = [
        migrations.AddField(
            model_name='permitrequestvalidation',
            name='comment_after',
            field=models.TextField(blank=True, verbose_name='Commentaires (après)'),
        ),
        migrations.AddField(
            model_name='permitrequestvalidation',
            name='comment_before',
            field=models.TextField(blank=True, verbose_name='Commentaires (avant)'),
        ),
        migrations.AddField(
            model_name='permitrequestvalidation',
            name='comment_during',
            field=models.TextField(blank=True, verbose_name='Commentaires (pendant)'),
        ),
        migrations.AlterField(
            model_name='permitrequestvalidation',
            name='validation_status',
            field=models.IntegerField(choices=[(0, 'En attente'), (1, 'Approuvé'), (2, 'Refusé')], default=0, verbose_name='Statut de validation'),
        ),
    ]