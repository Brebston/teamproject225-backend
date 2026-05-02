from PIL import Image

MAX_EVENT_IMAGES = 6
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _validate_images_count(images):
    if len(images) > MAX_EVENT_IMAGES:
        return f"Maximum {MAX_EVENT_IMAGES} images allowed."
    return None


def _validate_image_type(image):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        return "Only JPEG, PNG and WEBP images are allowed."
    return None


def _validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE:
        return "Each image must be smaller than 5 MB."
    return None


def _validate_image_content(image):
    try:
        img = Image.open(image)
        img.verify()
    except Exception:
        return "Invalid image file."
    return None


def validate_event_images(images):
    if not images:
        return None

    error = _validate_images_count(images)
    if error:
        return error

    for image in images:
        for validator in (
            _validate_image_type,
            _validate_image_size,
            _validate_image_content,
        ):
            error = validator(image)
            if error:
                return error

    return None
