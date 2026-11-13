from rest_framework import serializers

from .models import PromptConfig


class PromptAnaliseOSSerializer(serializers.Serializer):
    empresa = serializers.IntegerField(read_only=True)
    custom_text = serializers.CharField(allow_blank=True, max_length=12000)
    original_text = serializers.CharField(read_only=True)
    effective_text = serializers.CharField(read_only=True)
    is_customized = serializers.BooleanField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)


class GeminiHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'model'], default='user')
    text = serializers.CharField()


class GeminiMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    history = serializers.ListField(
        child=GeminiHistoryItemSerializer(),
        required=False,
        default=list,
    )


class GeminiResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    model_used = serializers.CharField(required=False, allow_null=True)


class PromptConfigSerializer(serializers.ModelSerializer):
    is_customized = serializers.BooleanField(read_only=True)
    effective_text = serializers.CharField(read_only=True)
    key_display = serializers.CharField(source='get_key_display', read_only=True)

    class Meta:
        model = PromptConfig
        fields = [
            'id', 'key', 'key_display', 'label',
            'custom_text', 'original_text',
            'is_customized', 'effective_text',
            'updated_at',
        ]
        read_only_fields = ['id', 'key', 'original_text', 'updated_at']
