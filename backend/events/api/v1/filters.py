import django_filters
from events.models import Event


class EventFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    author = django_filters.NumberFilter(field_name="author_id")

    created_after = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = Event
        fields = ["category", "author", "created_after", "created_before"]
