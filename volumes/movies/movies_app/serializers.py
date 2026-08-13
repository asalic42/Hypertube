from rest_framework import serializers

from movies_app.models import Movie


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = "__all__"


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
