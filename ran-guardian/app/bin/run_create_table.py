from google.cloud import storage
from google.cloud import bigquery
import pandas as pd
import io

def process_csv_to_bigquery(
    bucket_name,
    blob_name,
    dataset_id,
    table_id,
    project_id,
    if_exists='replace'  # Options: 'replace', 'append', 'fail'
):
    # Initialize clients
    storage_client = storage.Client(project=project_id)
    bigquery_client = bigquery.Client(project=project_id)

    # Define the table reference
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Check if table exists
    try:
        bigquery_client.get_table(table_ref)
        if if_exists == 'fail':
            raise ValueError(f"Table {table_ref} already exists!")
        write_disposition = {
            'replace': 'WRITE_TRUNCATE',
            'append': 'WRITE_APPEND'
        }.get(if_exists)
    except Exception:  # Table doesn't exist
        write_disposition = 'WRITE_EMPTY'

    # Get the blob from GCS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Download the content as string
    content = blob.download_as_string()

    # Read CSV with custom parameters
    df = pd.read_csv(
        io.BytesIO(content),
        sep=';',  # Custom separator
        decimal=',',  # European decimal format
        escapechar='\\',  # Handle escaping of special characters
        encoding='utf-8',
        quotechar='"',  # Handle quotes around fields
        doublequote=True  # Handle double quotes within quoted fields
    )

    # Clean column names - replace problematic characters
    # This creates a mapping of original to clean names
    original_columns = df.columns
    clean_columns = {
        col: col.replace('.', '_').replace('%', 'pct').replace('[', '_').replace(']', '_')
        for col in original_columns
    }

    # Rename columns to clean versions
    df = df.rename(columns=clean_columns)

    # Create schema mapping for BigQuery
    schema = []
    for column in df.columns:
        # Infer data type (you might want to customize this based on your needs)
        dtype = df[column].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            if 'int' in str(dtype):
                field_type = 'INTEGER'
            else:
                field_type = 'FLOAT'
        else:
            field_type = 'STRING'

        schema.append(bigquery.SchemaField(column, field_type))

    # Update job config with write disposition
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=write_disposition
    )

    # Convert DataFrame to newline-delimited JSON for loading
    json_data = df.to_json(orient='records', lines=True)

    # Load the data - convert string to bytes
    job = bigquery_client.load_table_from_file(
        io.BytesIO(json_data.encode('utf-8')),  # Convert to bytes
        table_ref,
        job_config=job_config
    )

    # Wait for the job to complete
    job.result()

    print(f"Loaded {job.output_rows} rows into {table_ref}")

    # Return mapping of original to clean column names for reference
    return clean_columns

# Example usage
if __name__ == "__main__":
    # Replace these with your actual values
    PROJECT_ID = "your-project-id"
    BUCKET_NAME = "your-bucket-name"
    BLOB_NAME = "your-file.csv"
    DATASET_ID = "your_dataset"
    TABLE_ID = "your_table"

    column_mapping = process_csv_to_bigquery(
        BUCKET_NAME,
        BLOB_NAME,
        DATASET_ID,
        TABLE_ID,
        PROJECT_ID
    )

    print("\nColumn name mapping:")
    for original, clean in column_mapping.items():
        print(f"Original: {original} -> Clean: {clean}")
