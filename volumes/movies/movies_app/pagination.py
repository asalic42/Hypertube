from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PagePagination(PageNumberPagination):
    """
    Page numbers rather than links: the front end loads `next_page` when the
    user scrolls, until it is null.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        page = self.page
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "pages": page.paginator.num_pages,
                "next_page": page.next_page_number() if page.has_next() else None,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "page", "pages", "next_page", "results"],
            "properties": {
                "count": {"type": "integer"},
                "page": {"type": "integer"},
                "pages": {"type": "integer"},
                "next_page": {"type": "integer", "nullable": True},
                "results": schema,
            },
        }
