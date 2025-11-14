from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserUserViewSet

from .pagination import FoodgramPagination
from .filters import IngredientFilter, RecipeFilter
from .permissions import RecipePermission, UserPermission
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Follow
from .serializers import (
    IngredientSerializer, RecipeReadSerializer, ShoppingCartSerializer,
    RecipeWriteSerializer, TagSerializer, FavoriteSerializer,
    SubscriptionSerializer, FollowCreateSerializer, AvatarSerializer
)


User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_ingredients__ingredient'
    )
    pagination_class = FoodgramPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    permission_classes = [RecipePermission]

    def get_serializer_class(self):
        """Подбирает сериализатор для чтения или записи."""
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавить рецепт в избранное."""
        return self._add_relation(FavoriteSerializer, request, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удалить рецепт из избранного."""
        return self._delete_relation(Favorite, request, pk)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавить рецепт в список покупок."""
        return self._add_relation(ShoppingCartSerializer, request, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удалить рецепт из списка покупок."""
        return self._delete_relation(ShoppingCart, request, pk)

    def _add_relation(self, serializer_class, request, pk):
        """Общий метод для добавления связей."""
        recipe = self.get_object()
        serializer = serializer_class(
            data={
                'user': request.user.id,
                'recipe': recipe.id
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _delete_relation(self, model, request, pk):
        """Общий метод для удаления связей."""
        recipe = get_object_or_404(Recipe, id=pk)
        deleted_count, _ = model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()

        if not deleted_count:
            return Response(
                {'errors': 'Рецепт не был добавлен.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.AllowAny],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = self.get_object()
        short_url = recipe.get_short_url(request)
        return Response({'short-link': short_url})

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


class UserViewSet(DjoserUserViewSet):
    """Вьюсет для работы с пользователями."""

    queryset = User.objects.all()
    pagination_class = FoodgramPagination
    permission_classes = [UserPermission]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        """Список подписок текущего пользователя."""
        authors = User.objects.filter(following__user=request.user)
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        """Подписаться на автора."""
        author = get_object_or_404(User, id=id)
        serializer = FollowCreateSerializer(
            data={'user': request.user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        """Отписаться от автора."""
        author = get_object_or_404(User, id=id)
        deleted_count, _ = Follow.objects.filter(
            user=request.user, author=author
        ).delete()

        if not deleted_count:
            return Response(
                {'error': 'Вы не подписаны на этого автора.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        """Загрузка аватара."""
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара."""
        user = request.user
        if user.avatar:
            user.avatar.delete()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
