import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    Ingredient, Recipe, RecipeIngredient, Tag, Favorite, ShoppingCart
)
from users.models import Follow


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Сериализатор для конвертации изображения в нужный формат."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            data = ContentFile(base64.b64decode(imgstr), name=file_name)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о пользователе."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли текущий пользователь на данного автора."""
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, author=obj).exists()
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов при записи рецепта."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов при чтении рецепта."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное."""
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.favorites.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверка, добавлен ли рецепт в список покупок."""
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.shopping_cart.filter(user=request.user).exists()
        )

    def get_image(self, obj):
        """Всегда возвращает строку с URL изображения."""
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        write_only=True,
        allow_empty=False,
        required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        allow_empty=False,
        required=True
    )
    image = Base64ImageField(
        required=True,
        allow_null=True
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'name', 'image', 'text', 'cooking_time'
        )

    def validate(self, data):
        """Общая валидация для создания и обновления."""
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError({
                'Должен быть хотя бы один ингредиент.'
            })
        ingredient_ids = [item['id'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError({
                'Ингредиенты не должны повторяться.'
            })
        tags = data.get('tags', [])
        if not tags:
            raise serializers.ValidationError({
                'Должен быть хотя бы один тег.'
            })
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError({
                'Теги не должны повторяться.'
            })

        return data

    @staticmethod
    def _create_recipe_ingredients(recipe, ingredients_data):
        """Создание ингредиентов рецепта через bulk_create."""
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = super().create(validated_data)
        recipe.tags.set(tags_data)
        self._create_recipe_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        instance.tags.set(tags_data)
        instance.recipe_ingredients.all().delete()
        self._create_recipe_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        """Возвращаем данные для чтения после создания/обновления."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецептов для избранного, подписок и т.д."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteShoppingCartSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранного и корзины покупок."""

    class Meta:
        fields = ('user', 'recipe')

    def validate(self, data):
        """Проверяем, что рецепт еще не добавлен."""
        user = data['user']
        recipe = data['recipe']
        model = self.Meta.model

        if model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже добавлен.')
        return data

    def to_representation(self, instance):
        """Возвращаем рецепт в кратком формате."""
        return RecipeShortSerializer(
            instance.recipe,
            context=self.context
        ).data


class FavoriteSerializer(FavoriteShoppingCartSerializer):
    """Сериализатор для избранного."""

    class Meta(FavoriteShoppingCartSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(FavoriteShoppingCartSerializer):
    """Сериализатор для корзины покупок."""

    class Meta(FavoriteShoppingCartSerializer.Meta):
        model = ShoppingCart


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для отображения подписок."""

    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes_count', 'recipes'
        )

    def get_is_subscribed(self, obj):
        """Всегда True для подписок."""
        return True

    def get_recipes_count(self, obj):
        """Подсчитывает количество рецептов автора."""
        return obj.recipes.count()

    def get_recipes(self, obj):
        """Возвращает краткую информацию о рецептах автора."""
        request = self.context.get('request')
        recipes = obj.recipes.all()

        if request:
            try:
                recipes_limit = int(request.query_params.get('recipes_limit'))
                recipes = recipes[:recipes_limit]
            except (TypeError, ValueError):
                pass

        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data


class FollowCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписок."""

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate(self, data):
        """Проверка на самоподписку и дублирование."""
        user = data.get('user')
        author = data.get('author')

        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора.'
            )

        return data

    def to_representation(self, instance):
        """Возвращаем данные в формате подписки."""
        return SubscriptionSerializer(
            instance.author, context=self.context
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки аватара."""
    avatar = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)
