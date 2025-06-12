import pyodbc
import os
from datetime import datetime, timedelta, date
from util import get_uid_pw, load_config


class ConnectorODBC:
    def __init__(self, config_path="config.json"):
        # Always load configuration from JSON file
        config = load_config(config_path)
        
        # Get db_type from config or use parameter
        db_type = config.get('db_type')
        
        # Load database queries from config file
        if 'database_queries' not in config or db_type not in config['database_queries']:
            raise ValueError(f"Database queries for '{db_type}' not found in config file '{config_path}'")
        
        self.config = config['database_queries'][db_type]
        
        # Auto-detect if environment variables are set
        use_env_vars = bool(os.getenv("SQLUSERNAMEENCODED") and os.getenv("SQLPWENCODED"))
        
        # Build connection string based on whether env vars are available
        if use_env_vars:
            # Use encoded credentials from environment (legacy method)
            user, pw = get_uid_pw()
            connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:h1b.database.windows.net,1433;Database=h1b;Uid={user};Pwd={pw};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

        else:
            # Build connection string from config
            if config.get("connection_string"):
                connection_string = config.get("connection_string")
            else:
                conn_config = config.get('connection', config)  # Support both nested and flat structure
                connection_string = (
                    f"Driver={{{conn_config.get('driver', 'ODBC Driver 18 for SQL Server')}}};"
                    f"Server={conn_config['server']};"
                    f"Database={conn_config['database']};"
                    f"Uid={conn_config['username']};"
                    f"Pwd={conn_config['password']};"
                    f"Encrypt={conn_config.get('encrypt', 'yes')};"
                    f"TrustServerCertificate={conn_config.get('trust_server_certificate', 'no')};"
                    f"Connection Timeout={conn_config.get('connection_timeout', 30)};"
                )
        
        self.conn = pyodbc.connect(connection_string)
        self.cursor = self.conn.cursor()
        
        # Inherit methods from the connection object
        for attr_name in dir(self.conn):
            if not attr_name.startswith('_') and not hasattr(self, attr_name):
                setattr(self, attr_name, getattr(self.conn, attr_name))



    def execute(self, query):
        print(query)
        self.cursor.execute(query)

    

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
        query = self.config["get_all_columns"]
        self.execute(query)
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
    
