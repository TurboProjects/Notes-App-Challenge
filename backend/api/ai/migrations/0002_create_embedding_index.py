from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_class WHERE relname='api_ai_notechunk') THEN "
                "   CREATE INDEX IF NOT EXISTS api_ai_notechunk_embedding_hnsw "
                "   ON api_ai_notechunk USING hnsw (embedding vector_hnsw_ops) "
                "   WITH (m=16, ef_construction=200); "
                "END IF; "
                "END $$;"
            ),
            reverse_sql=(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_class WHERE relname='api_ai_notechunk') THEN "
                "   DROP INDEX IF EXISTS api_ai_notechunk_embedding_hnsw; "
                "END IF; "
                "END $$;"
            ),
        ),
    ]
