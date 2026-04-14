# flights-data-engineering-a
End-to-end data engineering project on the 2015 U.S. flights dataset (~5.8M records). Builds a Medallion pipeline (S3, Glue, Athena), a PostgreSQL model, and delivers analytics, regression, and time series forecasting for flight delays and demand.

# Run bronze
```bash
uv run python etl/bronze.py --bucket itam-anlytics-karla --data-dir data/flights
```

# Run silver
```bash
uv run python etl/silver.py --bucket itam-anlytics-karla
```

# Screenshots

### ETL - Bronze
![Airlines - Bronze AWS Glue register and schema](images/airlines_bronze_glue_schema.png)
![Airports - Bronze AWS Glue register and schema](images/airports_bronze_glue_schema.png)
![Flights - Bronze AWS Glue register and schema](images/flights_bronze_glue_schema.png)

### ETL - Silver
![Flights daily - Silver AWS Glue register and schema](images/flights_daily_silver_glue_schema.png)
![Flights daily - Silver AWS Glue partitions](images/flights_daily_silver_glue_partitions.png)
![Flights monthly - Silver AWS Glue register and schema](images/flights_monthly_silver_glue_schema.png)
![Flights by airport - Silver AWS Glue register and schema](images/flights_by_airport_silver_glue_schema.png)
