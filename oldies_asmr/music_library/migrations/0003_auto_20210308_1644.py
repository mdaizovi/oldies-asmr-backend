# Generated by Django 3.1.7 on 2021-03-08 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music_library', '0002_song_description_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='citation_apa',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='song',
            name='citation_chicago',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='song',
            name='citation_mla',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
