import base64
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Follow


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


class UsernameValidationMixin:
    """Миксин для валидации имени пользователя."""

    FORBIDDEN_NAMES = {'me', 'admin', 'api', 'auth'}

    def validate_username(self, value):
        """Проверка имени пользователя."""
        value = value.strip().lower()

        if value in self.FORBIDDEN_NAMES:
            raise serializers.ValidationError(
                f'Имя "{value}" запрещено для использования.'
            )

        validator = UnicodeUsernameValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                'Имя может содержать только буквы, цифры и символы @/./+/-/_'
            )

        return value


class UserCreateSerializer(
    UsernameValidationMixin, serializers.ModelSerializer
):
    """Сериализатор для регистрации новых пользователей."""

    email = serializers.EmailField(
        max_length=254,
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    username = serializers.CharField(
        max_length=150,
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'password', 'first_name', 'last_name'
        )

    def create(self, validated_data):
        """Создание нового пользователя."""
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверен')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserSerializer(UsernameValidationMixin, serializers.ModelSerializer):
    """Сериализатор для отображения информации о пользователе."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли текущий пользователь на данного автора."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о подписках."""

    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='author.avatar', read_only=True)
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes_count', 'recipes'
        )

    def get_is_subscribed(self, obj):
        """Возвращает статус подписки на автора."""
        return True

    def get_recipes_count(self, obj):
        """Подсчитывает количество рецептов автора."""
        return obj.author.recipes.count()

    def get_recipes(self, obj):
        """Возвращает краткую информацию о рецептах автора."""
        from recipes.serializers import RecipeShortSerializer
        recipes_limit = int(
            self.context['request'].query_params.get('recipes_limit', 3)
        )
        recipes = obj.author.recipes.all()[:recipes_limit]

        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки аватара."""
    avatar = Base64ImageField(
        required=True,
        allow_null=True
    )

    class Meta:
        model = User
        fields = ('avatar',)
