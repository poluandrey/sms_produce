# Generated by Django 5.0.6 on 2024-05-15 14:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sms", "0004_broadcast_sent_sms"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcast",
            name="phone_number_length",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
