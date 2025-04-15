from ctransformers import AutoModelForCausalLM
import time
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
nv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path=nv_path)

class llm:
    def __init__(self, model='', version=''):
        self.model = model
        self.version = version
        self.llm = None
        self.template = '''[INST] You are a professional SQL developer.
Return only the SQL Server compatible query based on the question.
Use ONLY triple backticks to enclose the SQL code like this: ```SQL QUERY```.

Use the table(s): "{schema}".
Question: {prompt} [/INST]'''

    def load_model(self):
        """Loads the model either from local path or from Hugging Face if no local model is provided."""
        try:
            model_path = os.environ.get('MODEL_PATH', '')
            if not model_path:
                raise Exception("MODEL_PATH environment variable not set.")
            print(f"Loading model from: {model_path}")

            if self.model:
                llm_model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True)
            else:
                raise Exception("Model name is required to load the model.")

            self.llm = llm_model
            print("Model loaded successfully.")
            return llm_model

        except Exception as e:
            error_msg = f'Unable to find or load a local model. Error occurred: {e}'
            print(error_msg)
            return error_msg

    def response_capturer(self, schema, prompt):
        """Captures the SQL query from the model output."""
        try:
            start_time = time.time()
            formatted_template = self.template.replace("{schema}", schema).replace("{prompt}", prompt)

            if not self.llm:
                print("Model not loaded. Attempting to load the model...")
                model = self.load_model()
                if isinstance(model, str):
                    raise Exception(model)
            else:
                model = self.llm

            print(f"Generating response with prompt:\n{formatted_template}\n")

            # Generate full response using model
            full_output = model(formatted_template)
            print(f"Raw model output:\n{full_output}\n")

            # Extract SQL query from model's response
            sql_query = self.extract_sql_query(full_output)

            end_time = time.time()
            return sql_query, round(end_time - start_time, 2)

        except Exception as e:
            error_msg = f"Error in generating model response: {e}"
            print(error_msg)
            return error_msg, 0

    def extract_sql_query(self, response):
        """Extracts SQL query from model response, looking for triple backticks."""
        match = re.search(r'```(?:sql)?\s*([\s\S]*?)```', response, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Otherwise, fallback to first SQL-looking line
        for line in response.split('\n'):
            if line.strip().lower().startswith(("select", "insert", "update", "delete", "with")):
                return line.strip()

        return response.strip()  # Last resort fallback

# Test this file directly
if __name__ == "__main__":
    llm_model = llm(model=os.environ.get("MODEL_PATH", ""))

    schema_name = "your_table_schema"
    prompt = "Write an SQL query to select all rows from the table where the column 'age' is greater than 25."

    query, time_taken = llm_model.response_capturer(schema_name, prompt)

    print(f"\nGenerated SQL Query:\n{query}")
    print(f"Time Taken: {time_taken} seconds")
