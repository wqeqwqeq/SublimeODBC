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

## Quick Start

### 1. Set Up Credentials

- Press `Ctrl+M, Ctrl+P` to set your DBMS username and password (stored as environment variables, base64-encoded).

### 2. Start a Connection

- Press `Ctrl+E, Ctrl+O` to start an ODBC connection to your configured DBMS.

### 3. Run a Query

- Select your SQL and press `Ctrl+E, Ctrl+E` to execute. Results appear in a new tab or output panel.

### 4. Use Auto-Completion

- As you type SQL, completions for DB, schema, table, and columns will appear, based on your metadata.

### 5. Manage Metadata

- Press `Ctrl+M, Ctrl+I` to initialize metadata for the current DBMS.
- Use other `Ctrl+M` shortcuts to add/remove tables, update groups, or browse metadata.

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
|                    |   "timeout": 5,                  | Query timeout in seconds                    |
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
- There is an example connection group in snowflake and   

---

## Menus

A menu entry "SQLOdbc" is added to the main menu, with submenus for Connection, Metadata, Selection, and View, mirroring the key bindings.

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