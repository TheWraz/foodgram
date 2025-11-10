from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from api.pagination import FoodgramPagination
from .filters import IngredientFilter, RecipeFilter
from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .serializers import (
    IngredientSerializer, RecipeReadSerializer, RecipeShortSerializer,
    RecipeWriteSerializer, TagSerializer
)


class TagViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """Вьюсет для тегов."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """Вьюсет для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    pagination_class = FoodgramPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Кверисет для запросов к базе данных."""
        queryset = Recipe.objects.select_related('author').prefetch_related(
            'tags', 'recipe_ingredients__ingredient'
        )
        return queryset

    def get_serializer_class(self):
        """Подбирает сериализатор для чтения или записи."""
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_permissions(self):
        """Устанавливает права доступа."""
        if self.request.method in SAFE_METHODS:
            return []
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Устанавливает автора при создании рецепта."""
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        """Обновление рецепта с проверкой авторства."""
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта с проверкой авторства."""
        recipe = self.get_object()

        if recipe.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавить или удалить рецепт из избранного."""
        return self._add_remove_relation(Favorite, request, pk)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавить или удалить рецепт из списка покупок."""
        return self._add_remove_relation(ShoppingCart, request, pk)

    def _add_remove_relation(self, model, request, pk):
        """Общий метод для добавления или удаления связей."""
        recipe = self.get_object()

        if request.method == 'POST':
            if model.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже добавлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=request.user, recipe=recipe)
            recipe.refresh_from_db()
            serializer = RecipeShortSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            relation = model.objects.filter(user=request.user, recipe=recipe)
            if not relation.exists():
                return Response(
                    {'errors': 'Рецепт не был добавлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        """Получить прямую ссылку на рецепт."""
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/')
        recipe_url = base_url.replace(
            '/api/', '/').rstrip('/') + f'/recipes/{recipe.id}'

        return Response({'short-link': recipe_url})

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок с сумированием ингредиентов."""
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        ingredients = shopping_cart.values(
            'recipe__recipe_ingredients__ingredient__name',
            'recipe__recipe_ingredients__ingredient__measurement_unit'
        ).annotate(total_amount=Sum('recipe__recipe_ingredients__amount'))
        shopping_list = ["Список покупок:\n"]
        for ingredient in ingredients:
            name = ingredient['recipe__recipe_ingredients__ingredient__name']
            unit = ingredient[
                'recipe__recipe_ingredients__ingredient__measurement_unit'
            ]
            amount = ingredient['total_amount']
            shopping_list.append(f"{name} ({unit}) — {amount}")

        response = HttpResponse(
            '\n'.join(shopping_list), content_type='text/plain'
        )
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_list.txt"'
        return response
