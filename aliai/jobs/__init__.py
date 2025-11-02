"""
AliAI - Job Modules
Modular job functions for Airflow integration
"""

from .discover_product_ids import (
    discover_category_ids,
    discover_all_category_ids
)

from .update_product_details import (
    update_products_batch,
    update_single_product,
    update_high_priority_products
)

from .refresh_master_table import (
    refresh_category,
    mark_inactive_products,
    cleanup_failed_products
)

from .prioritize_products import (
    calculate_priorities,
    boost_category_priority
)

__all__ = [
    'discover_category_ids',
    'discover_all_category_ids',
    'update_products_batch',
    'update_single_product',
    'update_high_priority_products',
    'refresh_category',
    'mark_inactive_products',
    'cleanup_failed_products',
    'calculate_priorities',
    'boost_category_priority',
]

