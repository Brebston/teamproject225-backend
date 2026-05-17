from slugify import slugify


def generate_unique_slug(model, value, slug_field="slug"):
    slug = slugify(value)

    unique_slug = slug
    counter = 1

    while model.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1

    return unique_slug
