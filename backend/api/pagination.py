from rest_framework.pagination import PageNumberPagination

from foodgram.constants import PAGE_SIZE


class FoodgramPagination(PageNumberPagination):
    """Кастомная пагинация для Foodgram."""
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
