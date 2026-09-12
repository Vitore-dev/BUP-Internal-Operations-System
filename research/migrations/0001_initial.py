import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Study',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('short_summary', models.TextField(
                    blank=True,
                    help_text='Short summary shown to employees in the study directory',
                )),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('contact_phone', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pi', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='studies_as_pi',
                    to=settings.AUTH_USER_MODEL,
                    help_text='The Principal Investigator — owns the study. A study must always have one.',
                )),
                ('coordinator', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='studies_as_coordinator',
                    to=settings.AUTH_USER_MODEL,
                    help_text='Manages the study day-to-day, reports to the PI. Can be temporarily unassigned.',
                )),
                ('employees', models.ManyToManyField(
                    blank=True,
                    related_name='studies_as_member',
                    to=settings.AUTH_USER_MODEL,
                    help_text='Other staff on this study, distinct from the PI and coordinator.',
                )),
            ],
            options={
                'verbose_name': 'Study',
                'verbose_name_plural': 'Studies',
                'ordering': ['name'],
            },
        ),
    ]
