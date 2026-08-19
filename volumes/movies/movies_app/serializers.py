from rest_framework import serializers

from movies_app.models import Movie


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = "__all__"


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class ArchiveCatalogQuerySerializer(serializers.Serializer):
	q = serializers.CharField(required=False, allow_blank=True, default="")
	limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)


class ArchiveCatalogItemSerializer(serializers.Serializer):
	identifier = serializers.CharField()
	title = serializers.CharField()
	downloads = serializers.IntegerField()
	item_url = serializers.URLField()
	metadata_url = serializers.URLField()
	torrent_url = serializers.URLField()


class ArchiveCatalogResponseSerializer(serializers.Serializer):
	query = serializers.CharField()
	limit = serializers.IntegerField()
	results = ArchiveCatalogItemSerializer(many=True)


class ArchiveDownloadCreateSerializer(serializers.Serializer):
	identifier = serializers.CharField()
	destination_dir = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ArchiveDownloadStartResponseSerializer(serializers.Serializer):
	job_id = serializers.CharField()
	identifier = serializers.CharField()
	torrent_url = serializers.URLField()
	save_path = serializers.CharField()
	status = serializers.CharField()
	progress = serializers.FloatField()
	download_rate = serializers.IntegerField()
	upload_rate = serializers.IntegerField()
	num_peers = serializers.IntegerField()
	error = serializers.CharField(allow_null=True, required=False)
	message = serializers.CharField(allow_null=True, required=False)
	file_name = serializers.CharField(allow_null=True, required=False)
	created_at = serializers.FloatField()
	updated_at = serializers.FloatField()
	progress_url = serializers.URLField(required=False)


class ArchiveDownloadProgressResponseSerializer(serializers.Serializer):
	job_id = serializers.CharField()
	identifier = serializers.CharField()
	torrent_url = serializers.URLField()
	save_path = serializers.CharField()
	status = serializers.CharField()
	progress = serializers.FloatField()
	download_rate = serializers.IntegerField()
	upload_rate = serializers.IntegerField()
	num_peers = serializers.IntegerField()
	error = serializers.CharField(allow_null=True, required=False)
	message = serializers.CharField(allow_null=True, required=False)
	file_name = serializers.CharField(allow_null=True, required=False)
	created_at = serializers.FloatField()
	updated_at = serializers.FloatField()
