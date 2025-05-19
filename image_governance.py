from google.cloud import bigquery
from vertexai import generative_models
from vertexai.generative_models import GenerativeModel

# === Setup ===
project_id = "coe-landing-zone-18-ats-2246"
dataset_id = "gen_ai_hyper_personalised_ads"
input_table = "customer_image_buckets"
output_table = "customer_image_vqa"

# Load models
gemini_pro_vision_model = GenerativeModel("gemini-1.0-pro-vision")

# Clients
client = bigquery.Client()

# Pre-fetch table references
input_table_ref = client.dataset(dataset_id).table(input_table)
output_table_ref = client.dataset(dataset_id).table(output_table)

# === Fetch Data ===
query = f"""
    SELECT * FROM `{project_id}.{dataset_id}.{input_table}`
    WHERE Bucket_path IS NOT NULL
    LIMIT 2
"""
df = client.query(query).to_dataframe()

# === Function to Call Gemini Vision Model ===
def image_vqa_response(customer_id, name, bucket_path):
    try:
        image = generative_models.Part.from_uri(bucket_path, mime_type="image/png")

        prompt = (
            "What is shown in this image? "
            "Is the image Realistic or Animated? "
            "Is there a home/house in this image? "
            "Answer each question separately."
        )

        model_response = gemini_pro_vision_model.generate_content([prompt, image])
        vqa_text = model_response.candidates[0].content.parts[0].text

        # Insert into BigQuery
        row = {
            "Customer_id": int(customer_id),
            "NAME": name,
            "VQA_response": vqa_text
        }
        client.insert_rows_json(output_table_ref, [row])

    except Exception as e:
        print(f"[Error] Failed for customer {customer_id} ({name}): {e}")
        # Optional: log failed attempt into another table

# === Process Each Row ===
for _, row in df.iterrows():
    image_vqa_response(row["Customer_id"], row["NAME"], row["Bucket_path"])
