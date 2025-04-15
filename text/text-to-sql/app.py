from flask import Flask, request, render_template, jsonify, session
import os
import sys
import json
from dotenv import load_dotenv
from dbconnection import dbactivities
import pygwalker as pyg
import pandas as pd
from llama import llm
import time
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
nv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path=nv_path)

# Ensure all required environment variables are set
required_env_vars = ['FLASK_KEY', 'DB', 'USER', 'HOST', 'PORT', 'MODEL_PATH']
for var in required_env_vars:
    if var not in os.environ:
        logger.error(f"Missing environment variable {var}")
        sys.exit(1)  # Exit the application if any environment variable is missing

# Initialize the Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ['FLASK_KEY']

# Initialize DB and LLM models
dbcon = dbactivities()

# Initialize model loading
llm_model = llm('TheBloke/CodeLlama-7B-Instruct-GGUF', 'codellama-7b.Q5_0.gguf')
load_result = llm_model.load_model()

if isinstance(load_result, str):  # If error occurs
    logger.error(f"Unable to load model: {load_result}")
else:
    logger.info("Model loaded successfully.")

# Fetch SQL data schema
db_schema = dbcon.index()
logger.info('SQL data fetched successfully')

# Connection string
connectionstring = {
    'Database': os.environ['DB'],
    'user': os.environ['USER'],
    'host': os.environ['HOST'],
    'port': os.environ['PORT']
}

current_query = ''
current_table = 'nothing'
time_difference = 0

# Flask routes
@app.route('/', methods=['GET'])
def index():
    try:
        normalized_data = json.dumps(db_schema)
        normalized_data = json.loads(normalized_data)
        databases = dbcon.get_databases()
        logger.info("Returning main page with database connection info.")
        return render_template('index.html', json_data=normalized_data, db_data=connectionstring, dbs=databases)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/process_textarea', methods=['POST'])
def process_textarea():
    try:
        # Log the incoming request body for debugging
        content = request.get_json()
        logger.debug(f"Received data: {content}")

        schema = content.get('schema', '')
        user_prompt = content.get('query', '')

        if not schema or not user_prompt:
            logger.error("Schema or query not provided in the request body")
            return jsonify({'error': 'Schema or query not provided'}), 400

        # Log schema and user prompt
        logger.debug(f"Schema: {schema}")
        logger.debug(f"User query: {user_prompt}")

        # Start measuring the response time for the model
        start_time = time.time()
        
        logger.debug("Calling the response_capturer method to generate SQL query...")
        # Attempt to get the query and time taken from the model
        current_query, time_taken = llm_model.response_capturer(schema, user_prompt)

        # Log the raw result from the model for inspection
        logger.debug(f"Model raw response: {current_query}")

        # If no query is returned or it's just the word "Query", handle that case
        if not current_query or current_query.strip().lower() == "query":
            logger.error("Model returned an empty query or just the word 'Query'")
            return jsonify({'error': 'Model returned an empty query or invalid response'}), 500

        # Log the model's response and time taken
        logger.debug(f"Model response received: {current_query}")
        logger.debug(f"Time taken for model to generate query: {time_taken}")

        # Calculate the total time taken
        global time_difference
        time_difference = round(time_taken / 60, 2)
        logger.info(f"Time taken to generate SQL query: {time_difference} minutes")

        return jsonify({'query': current_query, 'time': time_difference})

    except Exception as e:
        # Log the specific error message
        logger.error(f"Error in processing textarea: {str(e)}")
        return jsonify({'error': f"Error in processing textarea: {str(e)}"}), 500

@app.route('/change_db', methods=['POST'])
def change_db():
    content = request.get_json()
    db = content['database']
    global connectionstring
    try:
        if db == connectionstring['Database']:
            return {'status': 300, 'msg': 'no need to change'}
        else:
            dbcon.switch_db(db)
            connectionstring['Database'] = db
            global db_schema
            db_schema = dbcon.index()
            return {'status': 200, 'msg': 'changed successfully'}
    except Exception as e:
        logger.error(f"Error while changing database: {str(e)}")
        return {'status': 600, 'msg': str(e)}

@app.route('/clean_query', methods=['POST'])
def clean_query():
    content = request.get_json()
    global current_query
    current_query = content['query']
    return 'done'

@app.route('/output_page')
def output_page():
    try:
        if current_query == '':
            logger.error("No query has been processed yet.")
            return jsonify({'error': 'No query has been processed yet'}), 400

        # Assuming dbcon.query_outputs(current_query) returns a dictionary or list
        table = json.loads(dbcon.query_outputs(current_query))
        if not table:
            logger.error("The result table is empty.")
            return jsonify({'error': 'No data returned from the query'}), 404

        global current_table
        current_table = table
        columns = list(table.keys())
        indices = list(table[columns[0]].keys()) if columns else []

        global time_difference
        return render_template('output.html', db_data=current_query, positions=indices, output=table, gpt_metadata={'tokens': 0, 'time_taken': time_difference})

    except Exception as e:
        logger.error(f"Error in output_page route: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/render_dashboard')
def render_dashboard():
    try:
        if isinstance(current_table, pd.DataFrame):
            df = current_table
        else:
            df = pd.DataFrame(current_table)
        walker = pyg.walk(df, hideDataSourceConfig=True)
        walker_html = walker.to_html()
        return walker_html
    except Exception as e:
        logger.error(f"Error in render_dashboard route: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)
