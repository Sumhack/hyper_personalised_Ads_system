import vertexai
from vertexai.language_models import TextGenerationModel
from google.cloud import bigquery
import pandas as pd
from datetime import datetime

# Initialize BigQuery client
client = bigquery.Client()

# GCP & BigQuery configuration (replace with secure config or env vars)
project_id = "<your-project-id>"
dataset_id = "gen_ai_hyper_personalised_ads"
source_table = "customer_personas"
target_table = "customer_prompts"

# Table references
table_ref = client.dataset(dataset_id).table(source_table)
table_ref2 = client.dataset(dataset_id).table(target_table)

# Example prompt and guiding instructions for the image generation
examples = (
    "Commercial photography, home loans advertisement, #009FE1, John, a 50-year-old Australian man, "
    "standing with his wife, looking at a picturesque house in Coffs Harbour, yearning, comforting holding hands, "
    "envisioning a peaceful and happy retirement together. Charming architecture, welcoming porch, soft golden light, realistic, HD"
)

instructions = """
Prompt Strategy:
1) What + Brand Guidelines
2) Action with Emotional High
3) Subject with Core Category Need
4) Environment with Photographic Details

Important Note:
1) MAKE SURE THE PROMPT IS LESS THAN 100 WORDS.
2) Return only the generated prompt.
"""

def build_prompt_for_enriched_prompt(persona, examples, instructions):
    """
    Construct a detailed prompt to feed into the Vertex AI model,
    based on a customer persona.
    """
    prompt = f"""Task: To create a prompt for generating an image based on a persona.

Persona:
{persona['NAME']}, a {persona['AGE']} year old, {persona['MARRIED_STATUS']} {persona['GENDER']}, 
from {persona['COUNTRY']} who is a {persona['PERSONA']} and loves spending most on {persona['PRODUCT']}, 
currently in the {persona['STAGES']} stage of looking for a buying this product.

To begin, describe {persona['NAME']} and the persona. 
For instance, {persona['NAME']} could be a {persona['AGE']} year old {persona['PERSONA']} {persona['GENDER']}, 
{persona['MARRIED_STATUS']}, who is currently in the {persona['STAGES']} stage 
of looking for this product.

Focus on an action with emotional high:
Consider an action that {persona['NAME']} could be doing and add an emotional memory to it.
For example, what could {persona['NAME']} be typically doing? Alone, or with their loved ones.

Describe the environment with photographic details:
Imagine {persona['NAME']} in a setting that reflects their journey.
For instance, {persona['NAME']} could be surrounded by their family or friends doing their favorite activity in their comfort zone.

Instructions:
{instructions}

Examples:
{examples}
"""
    return prompt

def extract_prompt_response(input_prompt):
    """
    Uses Vertex AI's text generation model (Text-Bison) to generate a concise image prompt.
    """
    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 1024,
        "top_p": 0.8,
        "top_k": 40
    }

    model = TextGenerationModel.from_pretrained("text-bison@001")

    response = model.predict(input_prompt, **parameters)
    return response.text

# Fetch data from BigQuery
query = f"SELECT * FROM `{project_id}.{dataset_id}.{source_table}` LIMIT 1"
query_job = client.query(query)
df = query_job.to_dataframe()

# Preprocessing: Convert birthdate to age
current_year = datetime.now().year
df['BIRTH_DATE'] = pd.to_datetime(df['BIRTH_DATE'])
df['AGE'] = current_year - df['BIRTH_DATE'].dt.year

# Transform boolean marriage status into readable format
df['MARRIED_STATUS'] = df['MARRIED_STATUS'].apply(lambda x: 'Married' if x else 'Unmarried')

# List to collect enriched rows with prompts
prompts_data = []

# Iterate through personas and generate prompts
for _, row in df.iterrows():
    persona_dict = row.to_dict()

    prompt_text = build_prompt_for_enriched_prompt(persona_dict, examples, instructions)
    generated_prompt = extract_prompt_response(prompt_text)

    persona_dict['prompts'] = generated_prompt
    prompts_data.append(persona_dict)

# Convert to DataFrame
prompts_df = pd.DataFrame(prompts_data)

# Select final output columns for loading
selected_columns = ['Customer_ID', 'NAME', 'prompts']
final_df = prompts_df[selected_columns]

print(final_df)

# Load into BigQuery (uncomment to execute)
# job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
# job = client.load_table_from_dataframe(final_df, table_ref2, job_config=job_config)
# job.result()
# print(f"Loaded {job.output_rows} rows into {dataset_id}:{target_table}")
