from django.contrib import admin

from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart
)
from foodgram.constants import (
    RECIPE_INGREDIENT_EXTRA, RECIPE_INGREDIENT_MIN_NUM
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = RECIPE_INGREDIENT_EXTRA
    min_num = RECIPE_INGREDIENT_MIN_NUM


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time', 'pub_date')
    list_filter = ('author', 'name', 'tags', 'pub_date')
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]
    readonly_fields = ('pub_date',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    list_filter = ('recipe', 'ingredient')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user', 'recipe')
