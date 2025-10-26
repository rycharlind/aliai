#!/bin/bash
set -e

# Set Airflow environment variables
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__FERNET_KEY=XD01FFTSIHWNESBuWKzEzqhHNtspfYBZgmNC-C0DW98=
export AIRFLOW__API__SECRET_KEY=your-secret-key-here

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h postgres -p 5432 -U airflow; do
  echo "PostgreSQL is not ready yet. Waiting..."
  sleep 2
done

echo "PostgreSQL is ready. Initializing Airflow database..."

# Initialize the Airflow database
airflow db migrate

echo "Airflow database initialized successfully!"
