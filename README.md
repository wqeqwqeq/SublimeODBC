# SQLOdbc Sublime Plugin

A Sublime Text plugin to help users connect to and interact with ODBC-compatible DBMS (such as SQL Server and Snowflake) directly from the editor. It provides a rich set of features for running queries, managing metadata, formatting SQL, and leveraging context-aware auto-completion.

---

## Features

- **ODBC Connection Management**: Easily connect to SQL Server, Snowflake, or any ODBC-compatible database.
- **Run SQL Queries**: Execute queries and view results in new tabs or output panels.
- **Auto-Completion**: Context-aware SQL completion for databases, schemas, tables, columns, and even table aliases.
- **Metadata Management**: Initialize, update, and browse metadata for fast and accurate completions.
- **Query Formatting**: Format SQL queries for readability.
- **UI Utilities**: Rename tabs, resize panes, sort tabs, and more.
- **Export & Transpose**: Export query results to CSV and transpose tables for analysis.
- **Cache**: Query results are cached for quick retrieval and reduced DB load.

---

## Installation

1. **Dependencies**:  
   - Python 3.x  
   - [pyodbc](https://github.com/mkleehammer/pyodbc)  
   - [tabulate](https://pypi.org/project/tabulate/)  
   - [sqlparse](https://pypi.org/project/sqlparse/)  
   - (These are included in the `lib/` folder for plugin use.)

2. **Setup**:  
   - Place the plugin folder (e.g., `SQLOdbc`) in your Sublime Text `Packages` directory.
   - Ensure your ODBC drivers are installed for your target DBMS.

3. **Configuration**:  
   - Edit `config.json` to add or modify DBMS connection strings and metadata queries.
   - Edit `SQL.settings` to set your default DBMS and connection group.

---

## Getting Started - Step by Step

Follow this onboarding guide to get up and running with SQLOdbc:

### Step 1: Configure Your Database Connection

First, you need to configure your ODBC connection string and database queries:

1. **Open Settings**: 
   - Via Command Palette: Press `Ctrl+Shift+P`, type "ODBC: Edit Setting"
   - Via Menu: Go to `SQLOdbc > View > Edit setting`
   - Via Keyboard: Press `Ctrl+U, Ctrl+S` to view current settings (read-only)

2. **Edit Connection Details**: Configure your ODBC connection string and database-specific queries in the settings file. This includes:
   - ODBC connection strings for your database
   - Database-specific metadata queries
   - Default connection preferences

### Step 2: Customize Key Bindings (Optional)

Personalize your keyboard shortcuts:

1. **Open KeyMap**:
   - Via Command Palette: Press `Ctrl+Shift+P`, type "ODBC: Edit KeyMap"
   - Via Menu: Go to `SQLOdbc > View > Edit KeyMap`


2. **Customize**: Modify key bindings to match your preferences

### Step 3: Save Database Credentials as environmental variable (Optional)

Configure your database username and password:

- Press `Ctrl+M, Ctrl+P` to set your DBMS credentials
- Credentials are stored as environment variables (base64-encoded for security)
- **Don't change `SQL_USERNAME_ENCODED` and `SQL_PW_ENCODED` as they are reserved for environmental variable for password setup**
- skip or overwrite the entire connection string if you don't want to store your password as environmental variable

### Step 4: Start Your Database Connection

Connect to your database using any of these methods:

- **Keyboard**: Press `Ctrl+E, Ctrl+O`
- **Command Palette**: Press `Ctrl+Shift+P`, type "ODBC: Start Connection"  
- **Menu**: Go to `SQLOdbc > Connection > Start Connection`



### Step 5: Test with a Simple Query

Try running a basic query to confirm everything works:

1. **For Snowflake users**: Type `select current_user()` in a new file
2. **For SQL Server users**: Try `SELECT @@VERSION`
3. **Execute**: Select your query text and press `Ctrl+E, Ctrl+E`
4. **Results**: View results in a new tab or output panel

### Step 6: Explore Auto-Completion

The plugin includes example database schema for testing auto-completion:

1. **Start typing SQL**: Begin with `SELECT * FROM `
2. **Trigger completion**: Press `Ctrl+Space` to see available databases, schemas, tables, and columns
3. **Explore**: Try typing table aliases and see column suggestions appear automatically
4. **Example**: The plugin includes sample connection groups you can use to test completions
5. To view the example auto completion, see `SQLOdbc > View > Edit Conn Group Schema`

### Step 7: Load Your Database Metadata

Get comprehensive metadata from your database for full auto-completion support:

1. **Initialize Metadata**:
   - **Keyboard**: Press `Ctrl+M, Ctrl+I`
   - **Command Palette**: "ODBC: Get All metadata from DBMS"
   - **Menu**: `SQLOdbc > Metadata > Get All metadata from DBMS`

2. **Wait for completion**: This process will scan your entire database environment (can take a few minutes for large databases)

3. **Enjoy full completions**: Once complete, you'll have auto-completion for all accessible databases, schemas, tables, and columns in your environment

### Step 8: Manage Connection Groups (Advanced)

#### Understanding Connection Groups and DBMS Switching

**Connection Groups** are collections of database objects (schemas, tables, columns) organized for efficient metadata management and auto-completion. Each connection group belongs to a specific DBMS and contains curated sets of tables and their metadata.

**Switching Between DBMS**: To work with different database systems (e.g., SQL Server vs Snowflake):

1. **Choose DBMS Connection**:
   - **Keyboard**: Press `Ctrl+M, Ctrl+C`
   - **Command Palette**: "ODBC: Choose DBMS Connection"
   - **Menu**: `SQLOdbc > Connection > Choose DBMS Connection`

2. **Select Connection Group**: After switching DBMS, choose the appropriate connection group:
   - **Keyboard**: Press `Ctrl+M, Ctrl+S`
   - **Command Palette**: "ODBC: Select Conn Group"

**Important Notes**:
- Connection groups are **managed separately per DBMS** - your Snowflake groups won't appear when connected to SQL Server
- Each DBMS maintains its own metadata structure and connection groups
- You can have multiple connection groups per DBMS for different projects or data domains


Organize your database objects into connection groups for better management:

- **Create groups**: Press `Ctrl+M, Ctrl+N` to create new connection groups
- **Add specific tables**: Press `Ctrl+M, Ctrl+A` to add tables to a group
- **Browse metadata**: Press `Ctrl+M, Ctrl+B` to explore your connection group's metadata
- **Switch groups**: Press `Ctrl+M, Ctrl+S` to select different connection groups


## Quick Reference

### Essential Shortcuts
- `Ctrl+E, Ctrl+O`: Start connection
- `Ctrl+E, Ctrl+E`: Run selected SQL
- `Ctrl+M, Ctrl+P`: Set credentials  
- `Ctrl+M, Ctrl+I`: Load all metadata
- `Ctrl+Space`: Trigger auto-completion
- `Ctrl+Shift+P`: Open Command Palette (access all commands)

---

## Key Bindings

The key bindings are organized by their source files:

### SQLQueryHelper.py Commands
| Key Binding        | Command                          | Description                                 |
|--------------------|----------------------------------|---------------------------------------------|
| Ctrl+Q             | `expand_selection_to_semicolon`  | Expand selection to nearest semicolon       |
| Ctrl+E, Ctrl+B     | `sa_format`                      | Format SQL selection                        |

### SQLExecute.py Commands
| Key Binding        | Command                          | Description                                 |
|--------------------|----------------------------------|---------------------------------------------|
| Ctrl+E, Ctrl+O     | `so_start_conn`                  | Start ODBC connection                       |
| Ctrl+E, Ctrl+E     | `so_run_sql_cmd`                 | Run SQL command                             |
|                    | args: `{                         |                                             |
|                    |   "limit": 300,                  | Maximum rows to fetch                       |
|                    |   "number_of_cache_query": 20,   | Number of queries to cache                  |
|                    |   "timeout": 30,                 | Query timeout in seconds                    |
|                    |   "output_in_panel": false,      | Show results in panel vs new tab            |
|                    |   "queries": null                | Optional query override                     |
|                    | }`                               |                                             |
| Ctrl+E, Ctrl+C     | `sa_clear_cache`                 | Clear query result cache                    |
| Ctrl+E, Ctrl+I     | `sa_interrupt_query`             | Interrupt running query                     |
| Ctrl+E, Ctrl+R     | `so_restart_connection`          | Restart database connection                 |
| Ctrl+E, Ctrl+V     | `so_tbl_to_csv`                  | Export query results to CSV                 |
| Ctrl+E, Ctrl+P     | `tbl_transpose`                  | Transpose query results                     |
| Ctrl+E, Ctrl+F     | `so_remove_cache_file`           | Remove cache file from disk                 |

### SQLMetaData.py Commands
| Key Binding        | Command                          | Description                                 |
|--------------------|----------------------------------|---------------------------------------------|
| Ctrl+M, Ctrl+I     | `meta_init`                      | Initialize metadata                         |
|                    | args: `{"include_dtype": "True"}`| Include data types in metadata              |
| Ctrl+M, Ctrl+N     | `meta_new_conn_group`            | Create new connection group                 |
|                    | args: `{"include_dtype": "True"}`| Include data types in metadata              |
| Ctrl+M, Ctrl+P     | `meta_password`                  | Set DBMS username/password                  |
| Ctrl+M, Ctrl+C     | `meta_choose_connection`         | Choose DBMS connection                      |
| Ctrl+M, Ctrl+D     | `meta_delete_connection`         | Delete connection group                     |
| Ctrl+M, Ctrl+B     | `meta_browse_connection`         | Browse metadata columns                     |
| Ctrl+M, Ctrl+U     | `meta_update_connection_group`   | Update connection group metadata            |
|                    | args: `{"include_dtype": "True"}`| Include data types in metadata              |
| Ctrl+M, Ctrl+A     | `meta_add_table_in_conn_group`   | Add table to connection group               |
|                    | args: `{"include_dtype": "True"}`| Include data types in metadata              |
| Ctrl+M, Ctrl+R     | `meta_remove_table_in_conn_group`| Remove table from connection group          |
|                    | args: `{"include_dtype": "True"}`| Include data types in metadata              |
| Ctrl+M, Ctrl+S     | `meta_select_connection`         | Select connection group                     |

### SQLUiHelper.py Commands
| Key Binding        | Command                          | Description                                 |
|--------------------|----------------------------------|---------------------------------------------|
| Ctrl+U, Ctrl+K     | `view_config`                    | View key bindings                           |
|                    | args: `{                         |                                             |
|                    |   "read_only": true,             | Display in read-only mode                   |
|                    |   "file": "keymap"               | View keymap file                            |
|                    | }`                               |                                             |
| Ctrl+U, Ctrl+S     | `view_config`                    | View settings                               |
|                    | args: `{                         |                                             |
|                    |   "read_only": true,             | Display in read-only mode                   |
|                    |   "file": "setting"              | View settings file                          |
|                    | }`                               |                                             |
| Ctrl+U, Ctrl+C     | `view_config`                    | View current schema                         |
|                    | args: `{                         |                                             |
|                    |   "read_only": true,             | Display in read-only mode                   |
|                    |   "file": "schema"               | View schema file                            |
|                    | }`                               |                                             |
| Ctrl+U, Ctrl+U     | `view_config`                    | View current connection info                |
| Ctrl+U, Ctrl+R     | `rename_view`                    | Rename current view/tab                     |
| Ctrl+U, Ctrl+Z     | `view_zoom`                      | Zoom in                                     |
|                    | args: `{"zoomin": true}`         |                                             |
| Ctrl+U, Ctrl+X     | `view_zoom`                      | Zoom out                                    |
|                    | args: `{"zoomin": false}`        |                                             |
| Ctrl+U, Ctrl+T     | `sort_tabs_in_order`             | Sort tabs alphabetically                    |
| F1                 | `resize_window_group`            | Max/Minimize query result panel             |
| Ctrl+Alt+Right     | `set_layout`                     | Split view right                            |
|                    | args: `{                         |                                             |
|                    |   "cols": [0.0, 0.55, 1.0],      | Column layout                               |
|                    |   "rows": [0.0, 1.0],            | Row layout                                  |
|                    |   "cells": [[0,0,1,1],[1,0,2,1]] | Cell layout                                 |
|                    | }`                               |                                             |
| Ctrl+Alt+Down      | `set_layout`                     | Split view down                             |
|                    | args: `{                         |                                             |
|                    |   "cols": [0.0, 1.0],            | Column layout                               |
|                    |   "rows": [0.0, 0.55, 1.0],      | Row layout                                  |
|                    |   "cells": [[0,0,1,1],[0,1,1,2]] | Cell layout                                 |
|                    | }`                               |                                             |

---

## Project Structure

```
SQLOdbc/
├── SQLExecute.py              # Main execution logic and connection handling
├── SQLMetaData.py            # Metadata management and connection groups
├── SQLQueryHelper.py         # SQL formatting and selection utilities
├── SQLUIhelper.py            # UI utilities and window management
├── SQLAutoComplete.py        # SQL auto-completion implementation
├── SQL.sublime-completions   # Sublime Text completion definitions
├── SQL.settings              # User settings and preferences
├── config.json              # DBMS connection configurations
├── Main.sublime-menu        # Plugin menu definitions
├── Main.sublime-commands    # Command palette entries
├── Default (Windows).sublime-keymap  # Key bindings
├── Tab Context.sublime-menu # Context menu definitions
├── .no-sublime-package      # Package marker
├── .python-version          # Python version specification
├── .gitignore              # Git ignore rules
│
├── SQLAPI/                  # Core API implementation
│   ├── __init__.py
│   ├── connect.py          # ODBC connection handling
│   └── util.py             # Utility functions
│
├── lib/                     # Third-party dependencies
│   ├── pyodbc/             # ODBC database driver
│   ├── tabulate/           # Table formatting
│   ├── sqlparse/           # SQL parsing
│   └── wcwidth/            # Character width utilities
│
└── metastore/              # Metadata and cache storage
    └── <dbms>/             # Per-DBMS metadata
        └── <group>/        # Connection group metadata
```

---

## Metadata & Autocomplete

- Metadata is stored in `metastore/<dbms>/<group>/` as JSON and text files.
- Auto-completion uses this metadata for fast, context-aware suggestions.
- Use the `meta_*` commands to manage and refresh metadata as your schema changes.
- There are example connection groups included for reference and testing.

---

## Menus

The plugin adds a comprehensive "SQLOdbc" menu to the main menu bar with the following structure:

### Connection Menu
- **Start Connection**: Initialize ODBC connection
- **Choose DBMS Connection**: Select from available database connections
- **Run SQL Command**: Execute SQL queries with customizable options
- **Format SQL**: Format SQL code for readability
- **Clear Cache**: Clear query result cache
- **Interrupt Query**: Stop currently running queries
- **Restart Connection**: Restart the database connection
- **Remove Cache File**: Delete cache files from disk

### Metadata Menu
- **Get All metadata from DBMS**: Initialize complete metadata from database
- **New Conn Group**: Create new connection group
- **Password**: Set database credentials
- **Delete Conn Group**: Remove connection group
- **Browse All Cols in Conn Group**: Browse metadata columns
- **Refresh Meta in Conn Group**: Update connection group metadata
- **Add Table to Conn Group**: Add specific tables to connection group
- **Remove Table from Conn Group**: Remove tables from connection group
- **Select Conn Group**: Choose active connection group
- **Select Query split by Semicolon**: Expand selection to semicolon

### UI Menu
- **Rename View**: Rename current tab/view
- **Zoom In/Out**: Adjust view zoom level
- **Sort Tabs in Order**: Sort tabs alphabetically
- **Split Right/Down**: Split editor layout
- **Max/Min Query Result Panel**: Toggle result panel size

### View Menu
- **View ConnGroup Schema (Read Only)**: View current schema
- **Edit KeyMap**: Customize key bindings
- **Edit setting**: Modify plugin settings
- **Edit ConnGroup Schema**: Edit schema configuration
- **View Current Conn**: Display current connection info

All menu items correspond to commands available in the Command Palette (Ctrl+Shift+P) with "ODBC:" prefix.

---

## Command Palette

All plugin functionality is accessible through the Command Palette (Ctrl+Shift+P). Commands are prefixed with "ODBC:" for easy discovery:

### Connection Commands
- `ODBC: Start Connection`
- `ODBC: Run SQL Query`
- `ODBC: Format SQL`
- `ODBC: Clear Query Cache`
- `ODBC: Interrupt Query`
- `ODBC: Restart Connection`
- `ODBC: Export to CSV`
- `ODBC: Transpose Table`
- `ODBC: Remove Cache File`

### Metadata Commands
- `ODBC: Get All metadata from DBMS`
- `ODBC: New Connection Group`
- `ODBC: Set Password`
- `ODBC: Choose DBMS Connection`
- `ODBC: Delete Conn Group`
- `ODBC: Browse All Cols Under Conn Group`
- `ODBC: Refresh Meta in Group`
- `ODBC: Add Table to Conn Group`
- `ODBC: Remove Table from Conn Group`
- `ODBC: Select Conn Group`

### View Commands
- `ODBC: View Current Schema`
- `ODBC: Edit ConnGroup Schema`
- `ODBC: View Current Connection`
- `ODBC: Edit KeyMap`
- `ODBC: Edit Setting`

### UI Commands
- `ODBC: Rename View`
- `ODBC: Zoom In`
- `ODBC: Zoom Out`
- `ODBC: Sort Tabs`
- `ODBC: Resize Window Group`
- `ODBC: Split Right`
- `ODBC: Split Down`

---

## Security

- Credentials are stored as user environment variables, base64-encoded.
- Never commit your credentials or sensitive config to version control.

---

## Troubleshooting

- If you see connection errors, ensure your ODBC driver is installed and your credentials are set.
- If completions are missing, re-initialize metadata (`Ctrl+M, Ctrl+I`).
- For more logs, check the Sublime Text console (`View > Show Console`).

---

## Contributing

Pull requests and issues are welcome! Please ensure your code is well-documented and tested.

---

## License

MIT License

---

**Enjoy querying your databases from Sublime Text!** 