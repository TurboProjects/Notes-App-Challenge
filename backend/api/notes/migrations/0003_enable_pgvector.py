from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Enable the pgvector extension (idempotent CREATE EXTENSION IF NOT EXISTS)."""

    dependencies = [
        ("notes", "0002_initial"),
    ]

    operations = [
        VectorExtension(),
    ]
