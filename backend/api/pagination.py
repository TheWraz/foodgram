from rest_framework.pagination import PageNumberPagination

from foodgram.constants import PAGE_SIZE, PAGE_SIZE_QUERY_PARAM


class FoodgramPagination(PageNumberPagination):
    """Кастомная пагинация для Foodgram."""
    page_size = PAGE_SIZE
    page_size_query_param = PAGE_SIZE_QUERY_PARAM
