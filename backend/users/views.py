from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.pagination import FoodgramPagination
from .models import Follow
from .serializers import (
    AvatarSerializer, FollowSerializer, PasswordSerializer,
    UserCreateSerializer, UserSerializer
)


User = get_user_model()


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    """Вьюсет для работы с пользователями."""

    queryset = User.objects.all()
    pagination_class = FoodgramPagination
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия."""
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """Настройка прав доступа для разных действий."""
        if self.action in ['create', 'list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        """Работа с собственным профилем пользователя."""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        """Список подписок текущего пользователя."""
        follows = Follow.objects.filter(
            user=request.user
        ).select_related('author')
        page = self.paginate_queryset(follows)
        serializer = FollowSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        """Подписаться или отписаться на автора."""
        author = get_object_or_404(User, id=pk)

        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Follow.objects.filter(
                user=request.user, author=author
            ).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            follow = Follow.objects.create(user=request.user, author=author)
            serializer = FollowSerializer(follow, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            try:
                follow = Follow.objects.get(user=request.user, author=author)
            except Follow.DoesNotExist:
                return Response(
                    {'error': 'Вы не подписаны на этого автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post', 'put', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        """Загрузка и удаление аватара."""
        user = request.user

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        """Смена пароля текущего пользователя."""
        serializer = PasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
