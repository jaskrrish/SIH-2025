# Generated manually for attachment encryption support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='is_encrypted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='attachment',
            name='security_level',
            field=models.CharField(blank=True, default='regular', max_length=20),
        ),
        migrations.AddField(
            model_name='attachment',
            name='encryption_metadata',
            field=models.JSONField(blank=True, null=True),
        ),
    ]

