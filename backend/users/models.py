from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

from foodgram.constants import MAX_LENGTH_FIRSTNAME, MAX_LENGTH_LASTNAME


class User(AbstractUser):
    """Кастомная модель пользователя."""

    email = models.EmailField(
        'Email',
        unique=True,
    )
    first_name = models.CharField(
        'Имя',
        max_length=MAX_LENGTH_FIRSTNAME,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_LENGTH_LASTNAME,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('email', 'username')

    def __str__(self):
        return self.email


class Follow(models.Model):
    """Модель для подписок пользователей."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow'
            ),
        )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
