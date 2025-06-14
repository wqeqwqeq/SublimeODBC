import pyodbc
import os
from util import get_uid_pw, load_settings
import sublime

class ConnectorODBC:
    def __init__(self, config_path="SQLOdbc.sublime-settings"):
        # First load settings to get current DBMS
        current_dbms = load_settings(get_cur_dbms_only=True)
        if not current_dbms:
            raise ValueError("current_dbms not found in settings")
        
        # Get database configuration for current DBMS
        db_config = load_settings(get_dbms_setting_only=True)
        if not db_config:
            raise ValueError(f"Database configuration for '{current_dbms}' not found in settings")
        
        self.config = db_config['database_queries']
        
        # Get connection string from config
        connection_string = db_config.get("connection_string")
        if not connection_string:
            raise ValueError(f"Connection string not found in settings for '{current_dbms}'")
        
        # Check if connection string has specific format placeholders we need to fill
        if '{SQL_USERNAME_ENCODED}' in connection_string or '{SQL_PW_ENCODED}' in connection_string:
            env_var_user = f'{current_dbms.upper()}USERNAMEENCODED'
            env_var_pw = f'{current_dbms.upper()}PWENCODED'
            
            if not os.getenv(env_var_user) or not os.getenv(env_var_pw):
                sublime.error_message(f"Environment variable {env_var_user} or {env_var_pw} not found")
                raise ValueError(f"Environment variable {env_var_user} or {env_var_pw} not found")
            
            # Get credentials from environment variables
            user, pw = get_uid_pw(env_var_user, env_var_pw)
            
            # Replace only the user and pwd placeholders, preserving driver name curly braces
            connection_string = connection_string.replace('{SQL_USERNAME_ENCODED}', user).replace('{SQL_PW_ENCODED}', pw)
        
        self.conn = pyodbc.connect(connection_string)
        self.cursor = self.conn.cursor()
        


    def execute(self, query):
        print(query)
        self.cursor.execute(query)

    def execute_many(self, queries):
        """Execute multiple SQL queries separated by semicolons.
        
        Args:
            queries (str): A string containing one or more SQL queries separated by semicolons.
            
        Returns:
            list: A list of results from each query execution.
        """
        # Split queries by semicolon and clean up
        for q in queries.split(';'):
            if len(set(q).intersection(set(["\n", "\r", "\t", " ",""])) ) == len(set(q)):
                continue
            try:
                self.execute(q)
                # Try to fetch results if any
            except Exception as e:
                # Add error to results and continue with next query
                print(f"Error executing query: {str(e)}")
        

    def close(self):
        if not self.conn.closed:
            self.conn.close()



    def _parse_meta_results(self, meta, include_dtype=True):
        """Helper function to parse metadata results into nested dictionary structure"""
        db_schema_tbl_col = {}
        db_list = []
        db_schema = {}
        db_schema_tbl = {}
        
        for row in meta:
            db, schema, table, col, dtype = row
            
            # Clean up names (remove spaces, convert to lowercase for consistency)
            db = db.replace(" ", "").lower() if db else "default"
            schema = schema.replace(" ", "").lower() if schema else "default"
            table = table.replace(" ", "").lower() if table else "unknown"
            col = col.replace(" ", "").lower() if col else "unknown"
            dtype = dtype.replace(" ", "").lower() if dtype else "unknown"
            
            # Build db list
            if db not in db_list:
                db_list.append(db)
            
            # Build db_schema mapping - now using nested dictionaries
            if db not in db_schema:
                db_schema[db] = {}
            if schema not in db_schema[db]:
                db_schema[db][schema] = {}
            
            # Build db_schema_tbl mapping - now using nested dictionaries for tables
            if db not in db_schema_tbl:
                db_schema_tbl[db] = {}
            if schema not in db_schema_tbl[db]:
                db_schema_tbl[db][schema] = {}
            if table not in db_schema_tbl[db][schema]:
                db_schema_tbl[db][schema][table] = {}
            
            # Initialize nested structure if not exists
            if db not in db_schema_tbl_col:
                db_schema_tbl_col[db] = {}
            if schema not in db_schema_tbl_col[db]:
                db_schema_tbl_col[db][schema] = {}
            if table not in db_schema_tbl_col[db][schema]:
                db_schema_tbl_col[db][schema][table] = {}
            
            # Add column data based on include_dtype flag
            if include_dtype:
                db_schema_tbl_col[db][schema][table][col] = dtype
            else:
                db_schema_tbl_col[db][schema][table][col] = ""
        
        return  db_list, db_schema, db_schema_tbl, db_schema_tbl_col
    
    def get_all_accessible_meta(self, include_dtype = True):
        """Get all accessible metadata using database-specific query from config"""
        query_config = self.config["get_all_columns"]
        
        # Handle nested query configuration (e.g. for Snowflake)
        if isinstance(query_config, dict):
            # First get list of databases
            list_db_query = query_config["list_db"]
            if ";" in list_db_query:
                self.execute_many(list_db_query)
                db_list_raw = self.cursor.fetchall()
            else:
                self.execute(list_db_query)
                db_list_raw = self.cursor.fetchall()

            databases = [row[0] for row in db_list_raw]
            
            # Initialize empty results
            all_meta = []
            
            # Query each database
            for db in databases:
                db_query = query_config["get_all_columns_under_db"].format(db)
                self.execute(db_query)
                db_meta = self.cursor.fetchall()
                all_meta.extend(db_meta)
            
            meta = all_meta
        else:
            # Handle simple query configuration (e.g. for SQL Server)
            self.execute(query_config)
            meta = self.cursor.fetchall()
        
        db_list, db_schema, db_schema_tbl, db_schema_tbl_col = self._parse_meta_results(meta, include_dtype)
        return db_list, db_schema, db_schema_tbl, db_schema_tbl_col

    def get_meta_under_db(self, db, include_dtype=True):
        """Get all accessible metadata under a specific database using database-specific query from config"""
        query = self.config["get_all_columns_under_db"]
        query = query.format(db)
        self.execute(query)
        meta = self.cursor.fetchall()
        
        db_list, db_schema, db_schema_tbl, db_schema_tbl_col = self._parse_meta_results(meta, include_dtype)
        return db_list, db_schema, db_schema_tbl, db_schema_tbl_col

    def get_meta_under_schema(self, database_schema, include_dtype=True):
        """Get all accessible metadata under a specific database and schema using database-specific query from config"""
        db, schema = database_schema.split('.')
        query = self.config["get_all_columns_under_schema"]
        query = query.format(db, schema)
        self.execute(query)
        meta = self.cursor.fetchall()
        
        db_list, db_schema, db_schema_tbl, db_schema_tbl_col = self._parse_meta_results(meta, include_dtype)
        return db_list, db_schema, db_schema_tbl, db_schema_tbl_col

    def get_meta_under_table(self, db_schema_table, include_dtype=True):
        """Get all accessible metadata under a specific database, schema, and table using database-specific query from config"""
        db, schema, table = db_schema_table.split('.')
        query = self.config["get_all_columns_under_table"]
        query = query.format(db, schema, table)
        self.execute(query)
        meta = self.cursor.fetchall()
        
        db_list, db_schema, db_schema_tbl, db_schema_tbl_col = self._parse_meta_results(meta, include_dtype)
        return db_list, db_schema, db_schema_tbl, db_schema_tbl_col

    def query_to_cur_transpose_compare(self, query):
        self.execute(query)
        lst = self.cursor.fetchall()
        cols = [ele[0] for ele in self.cursor.description]
        return [ele for ele in zip(cols, *lst) if len(set(ele[1:])) != 1]
    
