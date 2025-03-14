# Generated by Django 5.1.4 on 2025-01-08 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_apikey_counter_apikey_last_error_message_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MindMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='思维导图标题', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='创建时间')),
                ('document_id', models.IntegerField(default=0, help_text='关联的文档ID')),
                ('mind_map_json', models.JSONField(default=dict, help_text='思维导图JSON')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
