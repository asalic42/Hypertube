from django.conf import settings
from django.core.exceptions import ValidationError


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def validate_profile_picture_upload(uploaded_file):
    content_type = getattr(uploaded_file, "content_type", "")
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(
            "Le fichier doit être une image JPEG, PNG ou WebP."
        )

    max_upload_size = getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
    if uploaded_file.size > max_upload_size:
        raise ValidationError(
            f"L'image ne doit pas dépasser {max_upload_size} octets."
        )

    return uploaded_file