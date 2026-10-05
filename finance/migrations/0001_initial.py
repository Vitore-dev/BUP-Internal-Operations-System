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
            name='FinanceSourceFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='finance_sources/')),
                ('label', models.CharField(blank=True, help_text="e.g. 'Vendor Invoice #4521'", max_length=200)),
                ('page_count', models.PositiveIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FinanceDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FinanceSourceFilePage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_number', models.PositiveIntegerField(help_text='0-indexed position within the source file')),
                ('thumbnail', models.ImageField(upload_to='finance_thumbnails/')),
                ('source_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='finance.financesourcefile')),
            ],
            options={
                'ordering': ['page_number'],
                'unique_together': {('source_file', 'page_number')},
            },
        ),
        migrations.CreateModel(
            name='FinanceDocumentVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.PositiveIntegerField()),
                ('file', models.FileField(upload_to='finance_documents/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='finance.financedocument')),
            ],
            options={
                'ordering': ['-version_number'],
                'unique_together': {('document', 'version_number')},
            },
        ),
        migrations.CreateModel(
            name='FinanceDocumentPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='finance.financedocument')),
                ('source_page', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='used_in', to='finance.financesourcefilepage')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
