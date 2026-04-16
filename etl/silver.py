import argparse
import logging

import awswrangler as wr
import numpy as np
import pandas as pd


# ============================================================================
# Logging
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Args
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Build Silver tables for flights")

    parser.add_argument("--bucket", required=True, help="S3 bucket name")

    return parser.parse_args()


# ============================================================================
# Process single file
# ============================================================================

def load_silver(df, bucket: str, db_name: str, table_name: str, partition_cols=None, mode='overwrite'):
    wr.s3.to_parquet(
        df       = df,
        path     = f's3://{bucket}/flights/silver/{table_name}/',
        dataset  = True,
        database = db_name,
        table    = table_name,
        partition_cols=partition_cols,
        mode=mode
    )

    print(f"Silver/{table_name}: {len(df):,} rows.")
    
def create_flights_daily_table(bucket: str, db_name: str, db_name_bronze: str):

    table_name = "flights_daily"

    logging.info(f"Building {table_name}")
    wr.catalog.delete_table_if_exists(
        database=db_name,
        table=table_name)

    query = '''
        SELECT
            year,
            day,
            COUNT(*) AS total_flights,
            SUM(CASE WHEN departure_delay > 0 THEN 1 ELSE 0 END) AS total_delayed,
            SUM(CASE WHEN cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled,
            AVG(CASE WHEN cancelled = 0 THEN departure_delay END) AS avg_departure_delay,
            AVG(CASE WHEN cancelled = 0 THEN arrival_delay END) AS avg_arrival_delay,
            month
        FROM flights_bronze.flights
        GROUP BY year, month, day;
        '''

    flights_daily = wr.athena.read_sql_query(
        query,
        database=db_name,
        ctas_approach = False
    )
        
    # TODO: Agregar asserts
    logging.info("Loading to S3")
    load_silver(flights_daily, bucket, db_name, table_name, partition_cols=["month"], mode='overwrite_partitions')

    logger.info(f"Table registered: {db_name}.{table_name}")


def create_flights_monthly_table(bucket: str, db_name: str, db_name_bronze: str):

    table_name = "flights_monthly"

    logging.info(f"Building {table_name}")
    wr.catalog.delete_table_if_exists(
        database=db_name,
        table=table_name)

    query = '''
        SELECT
            month,
            airline,
        COUNT(*) AS total_flights,
        SUM(CASE WHEN departure_delay > 0 THEN 1 ELSE 0 END) AS total_delayed,
        SUM(CASE WHEN cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled,
        AVG(CASE WHEN cancelled = 0 THEN arrival_delay END) AS avg_arrival_delay,
        100.0 * AVG(
            CASE
                WHEN cancelled = 0 AND arrival_delay <= 15 THEN 1.0
                WHEN cancelled = 0 AND arrival_delay > 15 THEN 0.0
                ELSE NULL
            END
        ) AS on_time_pct
        FROM flights_bronze.flights
        GROUP BY month, airline
        '''

    flights_monthly = wr.athena.read_sql_query(
        query,
        database=db_name,
        ctas_approach = False
    )
        
    # TODO: Agregar asserts
    logging.info("Loading to S3")
    load_silver(flights_monthly, bucket, db_name, table_name)

    logger.info(f"Table registered: {db_name}.{table_name}")


def create_flights_by_airport_table(bucket: str, db_name: str, db_name_bronze: str):

    table_name = "flights_by_airport"

    logging.info(f"Building {table_name}")
    wr.catalog.delete_table_if_exists(
        database=db_name,
        table=table_name)

    query = '''
        SELECT
            origin_airport,
            COUNT(*) AS total_departures,
            SUM(CASE WHEN departure_delay > 0 THEN 1 ELSE 0 END) AS total_delayed,
            SUM(CASE WHEN cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled,
            AVG(CASE WHEN cancelled = 0 THEN departure_delay END) AS avg_departure_delay,
            100.0 * SUM(COALESCE(weather_delay, 0)) /
                NULLIF(
                    SUM(
                        COALESCE(air_system_delay, 0) +
                        COALESCE(security_delay, 0) +
                        COALESCE(airline_delay, 0) +
                        COALESCE(late_aircraft_delay, 0) +
                        COALESCE(weather_delay, 0)
                    ),
                    0
                ) AS pct_weather_delay
        FROM flights_bronze.flights
        GROUP BY origin_airport
        '''

    flights_by_airport = wr.athena.read_sql_query(
        query,
        database=db_name,
        ctas_approach = False
    )
        
    # TODO: Agregar asserts
    logging.info("Loading to S3")
    load_silver(flights_by_airport, bucket, db_name, table_name)

    logger.info(f"Table registered: {db_name}.{table_name}")


# ============================================================================
# Main
# ============================================================================
def main():
    args = parse_args()
    
    db_name = "flights_silver"
    db_name_bronze = "flights_bronze"
    
    logging.info("Ensuring Glue database exists: %s", db_name)
    wr.catalog.create_database(name=db_name, exist_ok=True)

    #TODO: Add asserts: DataFrame no está vacío, que las columnas clave no 
    # tienen nulos inesperados, y que los tipos son correctos
    #TODO: Add try/except y exits
    create_flights_daily_table(args.bucket, db_name, db_name_bronze)
    create_flights_monthly_table(args.bucket, db_name, db_name_bronze)
    create_flights_by_airport_table(args.bucket, db_name, db_name_bronze)
    
    # TODO: Al terminar la ejecución, el log debe mostrar el número de filas cargadas por tabla y las rutas S3 de destino.
    logger.info("Silver layer completed successfully")


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    main()
