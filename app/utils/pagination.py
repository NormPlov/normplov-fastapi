def paginate_results(items, page: int, page_size: int) -> dict:
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    return {
        "items": items[start_index:end_index],
        "metadata": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    }
