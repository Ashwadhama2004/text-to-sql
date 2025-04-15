import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
import json
from flask import Flask, render_template

# Initialize Flask app
app = Flask(__name__)

# Load environment variables from .env file
nv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path=nv_path)

class dbactivities:
    def __init__(self):
        self.host = os.environ['HOST']
        self.port = int(os.environ['PORT'])
        self.database = os.environ['DB']
        self.username = os.environ['USER']
        self.password = os.environ['PASSWORD']

        try:
            connection_string = f'postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}'
            self.engine = create_engine(connection_string)
            print(f'Connected to database: {self.database}')
        except Exception as e:
            print(f'Unable to establish a connection because of the below reason\n{e}')
            sys.exit(1)

        self.tables = []
        self.columns = []
        self.datatypes = []

    def get_databases(self):
        query = "SELECT datname FROM pg_database WHERE datistemplate = false;"
        with self.engine.connect() as connection:
            result = connection.execute(query)
            dbs = [row[0] for row in result]
        return dbs

    def switch_db(self, db):
        self.database = db
        try:
            connection_string = f'postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}'
            self.engine = create_engine(connection_string)
            print(f'Switched to database: {self.database}')
        except Exception as e:
            print(f'Unable to switch database:\n{e}')
            sys.exit(1)

    def get_tables(self):
        query = """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema;
        """
        with self.engine.connect() as connection:
            result = connection.execute(query)
            self.tables = [f'{row[0]}.{row[1]}' for row in result]
        
        print(f"Tables fetched: {self.tables}")  # Debugging output
        return self.tables

    def get_columns(self, table):
        schema, table_name = table.split('.')
        query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND table_schema = '{schema}'
        """
        df = pd.read_sql_query(query, self.engine)
        self.columns = df['column_name'].values
        self.datatypes = df['data_type'].values
        return self.columns, self.datatypes

    def query_outputs(self, query):
        df = pd.read_sql(query, self.engine)

        def is_overflow(value):
            try:
                json.dumps(value)
                return False
            except:
                return True

        def convert_overflow_values(df):
            for col in df.columns:
                for i in df.index:
                    if is_overflow(df.loc[i, col]):
                        df.loc[i, col] = str(df.loc[i, col])

        convert_overflow_values(df)
        return df.to_json(date_format='iso')

    def index(self):
        json_data = {}
        tables = self.get_tables()
        databases = self.get_databases()

        for table in tables:
            schema, table_name = table.split('.')
            columns, datatypes = self.get_columns(table)
            json_data[table_name] = [{
                'schema': schema,
                'name': ','.join(columns),
                'dtypes': ','.join(datatypes),
                'selected': True
            }]
        return json_data

# Initialize dbactivities
dbcon = dbactivities()

@app.get('/')
def index():
    db_schema=dbcon.index()
    # Fetching database schema and tables
    normalized_data = json.dumps(db_schema)
    normalized_data = json.loads(normalized_data)
    databases = dbcon.get_databases()
    tables = dbcon.get_tables()  # Get the tables
    connection_string = f"{dbcon.username}@{dbcon.host}:{dbcon.port}/{dbcon.database}"

    print(f"Tables in the database: {tables}")  # Debugging output
    return render_template('index.html', json_data=normalized_data, db_data=connection_string, dbs=databases, tables=tables)

if __name__ == '__main__':
    app.run(debug=True)
