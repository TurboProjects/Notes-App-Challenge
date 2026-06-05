"""Transport serializers (edge DTOs). They serialize domain entities: they
never touch ORM models directly and never leak past the controllers."""

from rest_framework import serializers

from api.notes.domain.entities import Question


class QuestionCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, trim_whitespace=True)


class CitationSerializer(serializers.Serializer):
    note_id = serializers.IntegerField(allow_null=True)
    note_title = serializers.CharField()
    chunk_id = serializers.IntegerField(allow_null=True)
    snippet = serializers.CharField()
    relevance_score = serializers.FloatField(allow_null=True)
    cited_order = serializers.IntegerField()


class AnswerSerializer(serializers.Serializer):
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    citations = CitationSerializer(many=True)


class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    answer = AnswerSerializer(allow_null=True)
    error = serializers.SerializerMethodField()

    def get_error(self, question: Question) -> dict | None:
        if question.error_code:
            return {"code": question.error_code}
        return None
