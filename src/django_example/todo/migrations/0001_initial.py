# Generated by Django 3.1.3 on 2020-11-18 17:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import l1ve.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(max_length=25)),
                ('added_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(max_length=25)),
                ('added_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_done', models.BooleanField(default=False)),
                ('text', models.TextField()),
                ('version_main', models.PositiveIntegerField(db_index=True, default=1, verbose_name="Version number for the 'all' versioning tree.")),
                ('added_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='todo.category')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
                ('tags', models.ManyToManyField(to='todo.Tag')),
                ('updated_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, l1ve.models.TreeVersioningMixin),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(max_length=25)),
                ('added_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='category',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='todo.group'),
        ),
        migrations.AddField(
            model_name='category',
            name='updated_by',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL),
        ),
    ]
