import argparse
import logging
from pathlib import Path

import pandas as pd
import awswrangler as wr


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
    parser = argparse.ArgumentParser(description="Bronze layer ingestion")

    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--data-dir", required=True, help="Local data directory")

    return parser.parse_args()


# ============================================================================
# Process single file
# ============================================================================
def process_normal_file(file_path: Path, bucket: str, db_name: str):
    table_name = file_path.stem
    logger.info(f"Processing {table_name}")

    df = pd.read_csv(file_path)

    s3_path = f"s3://{bucket}/{db_name}/bronze/{table_name}/"

    logger.info(f"Uploading to {s3_path}")

    wr.s3.to_parquet(
        df=df,
        path=s3_path,
        dataset=True,
        database=db_name,
        table=f"bronze_{table_name}",
        mode="overwrite"
    )

    logger.info(f"Table registered: {db_name}.bronze_{table_name}")

def process_large_file(
    file_path: Path,
    bucket: str,
    db_name: str,
    chunk_size: int = 500_000,
) -> None:
    table_name = file_path.stem
    table = f"bronze_{table_name}"
    s3_path = f"s3://{bucket}/{db_name}/bronze/{table_name}/"

    logger.info(f"Processing large file: {file_path}")
    logger.info(f"Target table: {db_name}.{table}")
    logger.info(f"Target path: {s3_path}")

    first_chunk = True

    for i, chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size), start=1):
        logger.info(f"Processing chunk {i} with shape {chunk.shape}")

        wr.s3.to_parquet(
            df=chunk,
            path=s3_path,
            dataset=True,
            database=db_name,
            table=table,
            mode="overwrite" if first_chunk else "append",
        )

        first_chunk = False

    logger.info(f"Finished loading large file: {table_name}")


# ============================================================================
# Main
# ============================================================================
def main():
    args = parse_args()

    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        raise ValueError(f"Data dir not found: {data_dir}")
    
    db_name = "flights"
    
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        raise ValueError("No CSV files found")

    logger.info(f"Found {len(csv_files)} files")

    wr.catalog.create_database(name=db_name, exist_ok=True)

    #TODO: Add asserts: DataFrame no está vacío, que las columnas clave no 
    # tienen nulos inesperados, y que los tipos son correctos
    #TODO: Add try/except y exits
    for file_path in csv_files:
        table_name = file_path.stem
        
        if table_name == "flights":
            process_large_file(file_path, args.bucket, db_name)
        else:
            process_normal_file(file_path, args.bucket, db_name)

    logger.info("Bronze layer completed successfully")


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    main()
