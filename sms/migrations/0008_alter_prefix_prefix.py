# Generated by Django 5.0.6 on 2024-07-09 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sms", "0007_remove_broadcast_prefix_prefix"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prefix",
            name="prefix",
            field=models.BigIntegerField(),
        ),
    ]