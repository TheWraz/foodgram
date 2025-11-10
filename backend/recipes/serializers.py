import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from users.serializers import UserSerializer
from .models import Ingredient, Recipe, RecipeIngredient, Tag


class Base64ImageField(serializers.ImageField):
    """Сериализатор для конвертации изображения в нужный формат."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            data = ContentFile(base64.b64decode(imgstr), name=file_name)
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        ]

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Проверка, добавлен ли рецепт в список покупок."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.shopping_cart.filter(user=request.user).exists()
        return False

    def get_image(self, obj):
        """Всегда возвращает строку с URL изображения."""
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return ""


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = serializers.ListField(
        child=serializers.DictField(),
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
        fields = [
            'ingredients', 'tags', 'name', 'image', 'text', 'cooking_time'
        ]

    def validate(self, data):
        """Общая валидация для создания и обновления."""
        if self.context['request'].method == 'PATCH':
            if 'ingredients' not in data:
                raise serializers.ValidationError(
                    'Поле ingredients обязательно.'
                )
            if 'tags' not in data:
                raise serializers.ValidationError(
                    'Поле tags обязательно.'
                )

        return data

    def validate_ingredients(self, value):
        """Валидация ингредиентов."""
        if not value:
            raise serializers.ValidationError(
                'Должен быть хотя бы один ингредиент.'
            )

        ingredients_id = [item['id'] for item in value]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        existing_id = set(Ingredient.objects.filter(
            id__in=ingredients_id).values_list('id', flat=True))
        for item in value:
            if item['id'] not in existing_id:
                raise serializers.ValidationError(
                    f'Ингредиент с id {item["id"]} не существует.'
                )
            if item.get('amount', 0) < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть не менее 1.'
                )

        return value

    def validate_tags(self, value):
        """Валидация тегов."""
        if not value:
            raise serializers.ValidationError('Должен быть хотя бы один тег.')
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Теги не должны повторяться.')

        return value

    def validate_cooking_time(self, value):
        """Валидация времени приготовления."""
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее 1 минуты.'
            )
        return value

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )

        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )

        return instance

    def to_representation(self, instance):
        """Возвращаем данные для чтения после создания/обновления."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецептов для избранного, подписок и т.д."""

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
