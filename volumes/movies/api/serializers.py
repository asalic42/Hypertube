from rest_framework import serializers

from api.models import Movie


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = [
            'title', 
            'description', 
            'release_date', 
            'director', 
            'genre', 
            'rating'
        ]


class MovieCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = [
            "title",
            "description",
            "release_date",
            "director",
            "genre",
            "rating"
        ]
