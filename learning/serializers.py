# learning/serializers.py
from rest_framework import serializers

class FillBlankSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    answer = serializers.CharField()

class MCQSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    selected_key = serializers.CharField()

class MatchingSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    pairs = serializers.ListField(child=serializers.DictField())

class PronunciationAttemptSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    expected_text = serializers.CharField()
    accuracy_score = serializers.FloatField()
    fluency_score = serializers.FloatField()
    completeness_score = serializers.FloatField()
    prosody_score = serializers.FloatField(required=False, default=0.0)

class TranslationRequestSerializer(serializers.Serializer):
    source_text_es = serializers.CharField()

class GlossaryEntrySerializer(serializers.Serializer):
    source_text_es = serializers.CharField()
    translated_text_gn = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")