"""
Пагинатор привычек: 5 элементов на страницу.
"""
from rest_framework.pagination import PageNumberPagination


class HabitPaginator(PageNumberPagination):
    """5 привычек на страницу, размер можно переопределить через ?page_size=."""

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 100
