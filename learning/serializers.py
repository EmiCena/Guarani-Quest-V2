# learning/serializers.py
from rest_framework import serializers


# ----- Written exercises -----
class FillBlankSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    answer = serializers.CharField()


class MCQSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    selected_key = serializers.CharField()


class MatchingSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    # Example: [{"left":"hola","right":"mba'éichapa"}, ...]
    pairs = serializers.ListField(child=serializers.DictField())


# ----- Pronunciation -----
class PronunciationAttemptSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    expected_text = serializers.CharField()
    accuracy_score = serializers.FloatField()
    fluency_score = serializers.FloatField()
    completeness_score = serializers.FloatField()
    prosody_score = serializers.FloatField(required=False, default=0.0)


# ----- Glossary -----
class TranslationRequestSerializer(serializers.Serializer):
    source_text_es = serializers.CharField()


class GlossaryEntrySerializer(serializers.Serializer):
    source_text_es = serializers.CharField()
    translated_text_gn = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ----- SRS (Spaced Repetition) -----
class SRSNextRequestSerializer(serializers.Serializer):
    # Reserved if you later support multiple decks; optional for now.
    deck_id = serializers.IntegerField(required=False)


class SRSGradeSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=0, max_value=5)

class BulkGlossaryListSerializer(serializers.Serializer):
    items = serializers.ListField(child=GlossaryEntrySerializer())

class DragDropSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    order = serializers.ListField(child=serializers.CharField())

class ListeningSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    selected_key = serializers.CharField()

class TranslationSubmissionSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    answer = serializers.CharField()