import django_filters

from .models import Recipe, Ingredient, Favorite, ShoppingCart, Tag


class RecipeFilter(django_filters.FilterSet):
    """Фильтры для рецептов по автору, тегам и избранному."""

    tags = django_filters.MultipleChoiceFilter(method='filter_tags')
    is_favorited = django_filters.CharFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.CharFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['tags'].extra['choices'] = [
            (tag.slug, tag.name) for tag in Tag.objects.all()
        ]

    def filter_tags(self, queryset, name, value):
        """Фильтр по тегам."""
        if not value:
            return queryset
        tags_slugs = value
        return queryset.filter(tags__slug__in=tags_slugs).distinct()

    def filter_is_favorited(self, queryset, name, value):
        """Фильтр по избранному."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                id__in=Favorite.objects.filter(
                    user=self.request.user
                ).values('recipe_id')
            )
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтр по списку покупок."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                id__in=ShoppingCart.objects.filter(
                    user=self.request.user
                ).values('recipe_id')
            )
        return queryset


class IngredientFilter(django_filters.FilterSet):
    """Фильтр для ингредиентов по названию."""

    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ingredient
        fields = ['name']
