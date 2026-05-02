from PIL import Image

MAX_EVENT_IMAGES = 6
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_event_images(images):
    if not images:
        return None

    if len(images) > MAX_EVENT_IMAGES:
        return f"Maximum {MAX_EVENT_IMAGES} images allowed."

    for image in images:
        content_type = getattr(image, "content_type", None)
        if content_type not in ALLOWED_IMAGE_TYPES:
            return "Only JPEG, PNG and WEBP images are allowed."

        if image.size > MAX_IMAGE_SIZE:
            return "Each image must be smaller than 5 MB."

        try:
            img = Image.open(image)
            img.verify()
        except Exception:
            return "Invalid image file."

    return None
