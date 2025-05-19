import vertexai
import numpy as np
import pandas as pd
from datetime import datetime

from google.cloud import bigquery, storage
from vertexai.preview.vision_models import ImageGenerationModel
from google.api_core.exceptions import InvalidArgument

# Initialize clients
bq_client = bigquery.Client()
project_id = "your-project-id"  # REDACTED
dataset_id = "gen_ai_hyper_personalised_ads"
source_table_name = "customer_prompts"
destination_table_name = "customer_image_buckets"
bucket_name = "hyper_personalised_ads"

# Reference to source table
source_table_ref = bq_client.dataset(dataset_id).table(source_table_name)
source_table = bq_client.get_table(source_table_ref)

# Query only selected customers for image generation
query = f"""
    SELECT * 
    FROM `{source_table.project}.{source_table.dataset_id}.{source_table.table_id}` 
    WHERE Customer_ID IN (2, 3, 4)
"""
df = bq_client.query(query).to_dataframe()

def image_generation_response(customer_id, name, prompt):
    """
    Generates an image from a prompt using Vertex AI, uploads it to GCS,
    and logs the path or error in BigQuery.
    """
    vertexai.init(project=project_id, location="us-central1")
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    bq_insert_client = bigquery.Client()

    dest_table_ref = bq_insert_client.dataset(dataset_id).table(destination_table_name)
    dest_table = bq_insert_client.get_table(dest_table_ref)

    try:
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1
        )

        # Define filename and path
        filename = f"imagen_{customer_id}_{name}.png"
        blob = bucket.blob(filename)
        bucket_path = f"gs://{bucket_name}/{filename}"

        # Upload image to GCS
        blob.upload_from_string(
            images[0]._image_bytes, content_type="image/png"
        )

        # Log success to BigQuery
        rows_to_insert = [{
            'Customer_id': int(customer_id),
            'NAME': name,
            'Bucket_path': bucket_path
        }]
        bq_insert_client.insert_rows_json(dest_table, rows_to_insert)

        return images

    except InvalidArgument as e:
        print(f"[ERROR] InvalidArgument: {e.message}")
        print("This may be due to policy violations in the prompt.")
        
        # Log failure to BigQuery
        rows_to_insert = [{
            'Customer_id': int(customer_id),
            'NAME': name,
            'Error_if_any': "No images were generated"
        }]
        bq_insert_client.insert_rows_json(dest_table, rows_to_insert)
        return None

# Process each row in the DataFrame
for _, row in df.iterrows():
    customer_id = row['Customer_ID']
    name = row['NAME']
    prompt = row['prompts']
    image_generation_response(customer_id, name, prompt)

