from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Follow


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'email', 'username', 'first_name', 'last_name', 'is_staff'
    )
    list_display_links = ('id', 'email')
    list_filter = ('email', 'username', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('id',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__email', 'author__email')
