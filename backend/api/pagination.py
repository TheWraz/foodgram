from rest_framework.pagination import PageNumberPagination


class FoodgramPagination(PageNumberPagination):
    """Кастомная пагинация для Foodgram."""
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100
