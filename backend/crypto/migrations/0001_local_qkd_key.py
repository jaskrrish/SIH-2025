from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LocalQKDKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key_id", models.CharField(max_length=100, unique=True)),
                ("requester_sae", models.CharField(max_length=255)),
                ("recipient_sae", models.CharField(max_length=255)),
                ("key_material_b64", models.TextField()),
                ("key_size", models.IntegerField(default=256)),
                ("algorithm", models.CharField(default="BB84", max_length=50)),
                ("expires_at", models.DateTimeField()),
                ("state", models.CharField(choices=[("stored", "Stored"), ("served", "Served"), ("consumed", "Consumed")], default="stored", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("served_at", models.DateTimeField(blank=True, null=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["requester_sae", "recipient_sae", "key_size"], name="crypto_loc_request_9113ed_idx"),
                    models.Index(fields=["expires_at"], name="crypto_loc_expires_a707f9_idx"),
                    models.Index(fields=["state"], name="crypto_loc_state_7c1b8e_idx"),
                ],
            },
        ),
    ]

