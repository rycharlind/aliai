"""
AliAI - Master Product Discovery Pipeline DAGs
Handles product ID discovery and batch updates from master_products table
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append('/Users/ryanlindbeck/Development/aliai')

from aliai.jobs import (
    discover_all_category_ids,
    update_products_batch,
    update_high_priority_products,
    mark_inactive_products,
    refresh_category,
    cleanup_failed_products,
    calculate_priorities
)


# Default arguments for DAGs
default_args = {
    'owner': 'aliai',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}


# ============================================================================
# DISCOVERY DAG - Run weekly to discover new product IDs
# ============================================================================
discovery_dag = DAG(
    'master_product_discovery',
    default_args=default_args,
    description='Weekly product ID discovery from categories',
    schedule='0 3 * * 0',  # Run weekly on Sunday at 3 AM
    max_active_runs=1,
    tags=['discovery', 'product-ids', 'weekly']
)


def run_discover_all():
    """Wrapper to run async discover_all_category_ids"""
    async def _discover():
        return await discover_all_category_ids(max_pages_per_category=10)
    
    result = asyncio.run(_discover())
    print(f"Discovery complete: {result}")
    return result


def run_calculate_priorities():
    """Wrapper to run async calculate_priorities"""
    async def _prioritize():
        return await calculate_priorities()
    
    return asyncio.run(_prioritize())


# Discovery tasks
discover_all_task = PythonOperator(
    task_id='discover_all_categories',
    python_callable=run_discover_all,
    dag=discovery_dag
)

calculate_priorities_task = PythonOperator(
    task_id='calculate_priorities',
    python_callable=run_calculate_priorities,
    dag=discovery_dag
)

# Task dependencies: discover first, then calculate priorities
discover_all_task >> calculate_priorities_task


# ============================================================================
# UPDATE DAG - Run daily to update product details
# ============================================================================
update_dag = DAG(
    'master_product_updates',
    default_args=default_args,
    description='Daily product detail updates from master table',
    schedule='0 4 * * *',  # Run daily at 4 AM
    max_active_runs=1,
    tags=['updates', 'product-details', 'daily']
)


def run_update_high_priority():
    """Wrapper to run async update_high_priority_products"""
    async def _update():
        return await update_high_priority_products(limit=50)
    
    return asyncio.run(_update())


def run_update_batch():
    """Wrapper to run async update_products_batch"""
    async def _update():
        return await update_products_batch(batch_size=200, priority_min=1, status_filter='pending')
    
    return asyncio.run(_update())


def run_mark_inactive():
    """Wrapper to run async mark_inactive_products"""
    async def _mark():
        return await mark_inactive_products(days_threshold=30)
    
    return asyncio.run(_mark())


# Update tasks
update_high_priority_task = PythonOperator(
    task_id='update_high_priority_batch',
    python_callable=run_update_high_priority,
    dag=update_dag
)

update_regular_batch_task = PythonOperator(
    task_id='update_regular_batch',
    python_callable=run_update_batch,
    dag=update_dag
)

mark_inactive_task = PythonOperator(
    task_id='mark_inactive_products',
    python_callable=run_mark_inactive,
    dag=update_dag
)

# Task dependencies: high priority first, then regular batch, then cleanup
update_high_priority_task >> update_regular_batch_task >> mark_inactive_task


# ============================================================================
# REFRESH DAG - Run weekly to refresh categories
# ============================================================================
refresh_dag = DAG(
    'master_product_refresh',
    default_args=default_args,
    description='Weekly category refresh to find new products',
    schedule='0 5 * * 0',  # Run weekly on Sunday at 5 AM
    max_active_runs=1,
    tags=['refresh', 'categories', 'weekly']
)


def run_cleanup_failed():
    """Wrapper to run async cleanup_failed_products"""
    async def _cleanup():
        return await cleanup_failed_products(error_threshold=5)
    
    return asyncio.run(_cleanup())


# Refresh tasks
cleanup_failed_task = PythonOperator(
    task_id='cleanup_failed_products',
    python_callable=run_cleanup_failed,
    dag=refresh_dag
)

# Single task DAG
cleanup_failed_task


# ============================================================================
# ON-DEMAND TASKS (for manual triggering)
# ============================================================================

# These can be run on-demand via Airflow UI
manual_discover_dag = DAG(
    'manual_discover_all',
    default_args=default_args,
    description='Manual trigger: Discover all product IDs',
    schedule=None,  # Manual trigger only
    tags=['manual', 'discovery']
)

manual_discover_task = PythonOperator(
    task_id='discover_all',
    python_callable=run_discover_all,
    dag=manual_discover_dag
)

manual_update_dag = DAG(
    'manual_batch_update',
    default_args=default_args,
    description='Manual trigger: Update product batch',
    schedule=None,  # Manual trigger only
    tags=['manual', 'updates']
)

manual_update_task = PythonOperator(
    task_id='update_batch',
    python_callable=run_update_batch,
    dag=manual_update_dag
)

