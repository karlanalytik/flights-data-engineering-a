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
    parser = argparse.ArgumentParser(description="Build Gold tables for flights")

    parser.add_argument("--bucket", required=True, help="S3 bucket name")

    return parser.parse_args()


# ============================================================================
# Process single file
# ============================================================================

def create_vuelos_analitica_table(bucket: str, db_name: str, db_name_bronze: str):

    table_name = "vuelos_analitica"
    s3_path = f"s3://{bucket}/flights/gold/{table_name}/"

    logging.info(f"Building {table_name}")
    wr.catalog.delete_table_if_exists(
        database=db_name,
        table=table_name)

    wr.s3.delete_objects(s3_path)

    query = f'''
        CREATE TABLE flights_gold.vuelos_analitica 
        WITH (
            format = 'PARQUET',
            write_compression = 'SNAPPY',
            external_location = '{s3_path}'
        ) AS (
            SELECT
                f.year,
                f.month,
                f.day,
                f.origin_airport,
                ap_orig.airport AS origin_airport_name,
                ap_orig.city AS origin_city,
                ap_orig.state AS origin_state,
                f.destination_airport,
                ap_dest.airport AS destination_airport_name,
                al.airline AS airline_name,
                f.departure_delay,
                f.arrival_delay,
                f.cancelled,
                f.cancellation_reason,
                f.distance,
                f.air_system_delay,
                f.airline_delay,
                f.weather_delay,
                f.late_aircraft_delay,
                f.security_delay
            FROM flights_bronze.flights f
            LEFT JOIN flights_bronze.airlines al
            ON f.airline = al.iata_code
            LEFT JOIN flights_bronze.airports ap_orig
            ON f.origin_airport = ap_orig.iata_code
            LEFT JOIN flights_bronze.airports ap_dest
            ON f.destination_airport = ap_dest.iata_code
        )
        '''

    wr.athena.read_sql_query(
        query,
        database=db_name,
        ctas_approach = False
    )
        
    logger.info(f"Table registered: {db_name}.{table_name}")


# ============================================================================
# Main
# ============================================================================
def main():
    args = parse_args()
    
    db_name = "flights_gold"
    db_name_bronze = "flights_bronze"
    
    logging.info("Ensuring Glue database exists: %s", db_name)
    wr.catalog.create_database(name=db_name, exist_ok=True)

    #TODO: Add asserts: DataFrame no está vacío, que las columnas clave no 
    # tienen nulos inesperados, y que los tipos son correctos
    #TODO: Add try/except y exits
    create_vuelos_analitica_table(args.bucket, db_name, db_name_bronze)
    
    # TODO: Al terminar la ejecución, el log debe mostrar el número de filas cargadas por tabla y las rutas S3 de destino.
    logger.info("Gold layer completed successfully")


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    main()
