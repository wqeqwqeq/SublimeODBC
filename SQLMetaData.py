import sublime
import sublime_plugin
import os
import time
import json
import threading
import ctypes
import shutil

from SQLAPI.connect import ConnectorODBC
from SQLAPI.util import load_package_path, crypt, load_settings, credential_set, update_settings

cache_path, lib_path, plugin_path, metastore_path = load_package_path()




# comment out since run_sql will create a global conn
# from run_sql import stop_thread


def stop_thread(t1):
    if isinstance(t1, int):
        thread_id = t1
    else:
        thread_id = t1.native_id
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        thread_id, ctypes.py_object(SystemExit)
    )
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        print("Exception raise failure")
    print(f"Successfull stop thread {thread_id}")







class MetaChooseConnection(sublime_plugin.WindowCommand):
    def run(self):
        self.config = load_settings()
        self.dbms_options = list(self.config.get('DBMS_Setting', {}).keys())
        self.window.show_quick_panel(
            self.dbms_options,
            self.on_select,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def on_select(self, index):
        if index == -1:
            return
        
        self.selected_dbms = self.dbms_options[index].upper()
        # Update current_dbms in settings
        try:
            update_settings('current_dbms', self.selected_dbms.lower())
            self.window.run_command("so_restart_connection")
        except Exception as e:
            sublime.message_dialog(f"Error updating settings: {str(e)}")


class MetaPassword(MetaChooseConnection):
    def on_select(self, index):
        self.selected_dbms = self.dbms_options[index].upper()
        if index == -1:
            return
        
        self.counter = 0
        self.prompts = [f"Enter {self.selected_dbms} Username", f"Enter {self.selected_dbms} Password"]
        self.show_prompt()

    def show_prompt(self):
        if self.counter == 0:
            panel = self.window.show_input_panel(
                self.prompts[self.counter], "", self.on_done, None, None
            )
        else:
            panel = self.window.show_input_panel(
                self.prompts[self.counter], "", self.on_done, None, None
            )
            panel.settings().set("password", True)

    def on_done(self, user_input):
        self.counter += 1
        user_input = crypt(user_input)
        
        if self.counter < len(self.prompts):
            # Store username
            os.system(
                f"""powershell -command "[System.Environment]::SetEnvironmentVariable('{self.selected_dbms}USERNAMEENCODED','{user_input}',[System.EnvironmentVariableTarget]::User)"
                """
            )
            self.show_prompt()
        else:
            # Store password
            os.system(
                f"""powershell -command "[System.Environment]::SetEnvironmentVariable('{self.selected_dbms}PWENCODED','{user_input}',[System.EnvironmentVariableTarget]::User)"
                """
            )
            sublime.message_dialog(
                f"{self.selected_dbms} Username and Password have been set\nPlease close and reopen sublime to enable system variables"
            )


def get_dbms_path():
    """Get the path for the current DBMS folder"""
    current_dbms = load_settings(get_cur_dbms_only=True)
    if not current_dbms:
        return metastore_path
    return os.path.join(metastore_path, current_dbms)


class MetaInit(sublime_plugin.WindowCommand):
    def run(self,include_dtype=True):
        def main_func(self,include_dtype):
            include_dtype = include_dtype.lower() == "true"
            conn = ConnectorODBC()
            panel = self.window.create_output_panel("meta_init")
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)

            # Create DBMS folder if it doesn't exist
            dbms_path = get_dbms_path()
            os.makedirs(dbms_path, exist_ok=True)

            # Create 'all' folder under DBMS folder
            all_folder_path = os.path.join(dbms_path, "all")
            create_metadata_folder(all_folder_path, "all", panel)

            # Get metadata from database
            panel.run_command(
                "append",
                {"characters": f"Retrieving all accessible metadata from EDW...\n"},
            )
            self.window.run_command("show_panel", {"panel": "output.meta_init"})

            # Get metadata without dtype
            db_list, db_schema, db_schema_tbl, db_schema_tbl_col = conn.get_all_accessible_meta(include_dtype=include_dtype)
            
            panel.run_command(
                "append",
                {"characters": f"Retrieved metadata for {len(db_list)} databases\n"},
            )

            # Create all metadata files
            drop_down_list = create_drop_down_list(db_schema_tbl_col)
            create_metadata_files(all_folder_path, db_list, db_schema, db_schema_tbl, db_schema_tbl_col, drop_down_list)

            # Create conn-group-component.txt with "all"
            create_conn_group_component(all_folder_path, db_list)


            # Print summary
            print_metadata_summary(panel, all_folder_path, db_list, drop_down_list)
            panel.set_read_only(True)
            self.window.run_command("show_panel", {"panel": "output.meta_init"})

            sublime.message_dialog(
                f"Successfully created metadata structure with {len(drop_down_list)} columns!"
            )

        if credential_set(show_msg=False) is False:
            # sublime.message_dialog(
            #     "Teradata username or password not setup\n use ctrl+e,ctrl+p to setup"
            # )
            # assert False
            self.window.run_command("meta_password")

        t1 = threading.Thread(
            target=main_func,
            args=[self,include_dtype],
            name="meta_init",
        )
        t2 = create_timeout_monitor_thread(self.window, t1, timeout=360, thread_name="meta_timeout")
        t1.start()
        t2.start()


class MetaNewConnGroup(sublime_plugin.WindowCommand):
    def run(self, include_dtype):
        if credential_set(show_msg=False) is False:
            sublime.message_dialog(
                "Teradata username or password not setup\n use ctrl+e,ctrl+p to setup"
            )
            assert False

        self.include_dtype = include_dtype.lower() == "true"
        input_panel = self.window.show_input_panel(
            "Table to add for autocomplete (In case multiple,split by comma): ",
            "e.g. db1.tbl,db2.tbl2,db.tbl3",
            self.on_done,
            None,
            None,
        )

    def on_done(self, tbl_to_pull):
        def main_func(self, tbl_to_pull):
            # Parse comma-separated input
            if "," in tbl_to_pull:
                tbl_list = tbl_to_pull.split(",")
            else:
                tbl_list = [tbl_to_pull]
            
            # Clean up the table list
            tbl_list = [
                tbl.strip().lower()
                for tbl in tbl_list
                if tbl.strip() not in ["", " ", "\n", "\t"]
            ]
            
            def on_execute(user_input):
                # Create connection group folder under DBMS folder
                dbms_path = get_dbms_path()
                connection_group_folder = os.path.join(dbms_path, user_input)
                create_metadata_folder(connection_group_folder, user_input, panel)
                
                # Create all metadata files
                db_list = list(combined_db_schema.keys())
                drop_down_list = create_drop_down_list(combined_db_schema_tbl_col)
                create_metadata_files(
                    connection_group_folder, 
                    db_list, 
                    combined_db_schema, 
                    combined_db_schema_tbl, 
                    combined_db_schema_tbl_col, 
                    drop_down_list,
                    group_name=user_input
                )
                
                # Create conn-group-component.txt with user inputs
                create_conn_group_component(connection_group_folder, tbl_list)
                
                
                # Print summary
                print_metadata_summary(panel, connection_group_folder, db_list, drop_down_list)
                
                self.window.run_command("meta_select_connection")
                sublime.message_dialog(
                    f"Successfully created connection group '{user_input}' with {len(drop_down_list)} columns!"
                )

            conn = ConnectorODBC()
            panel = self.window.create_output_panel("meta_add")
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)
            panel_text = ""

            # Initialize combined metadata structures
            combined_db_schema = {}
            combined_db_schema_tbl = {}
            combined_db_schema_tbl_col = {}

            # Process each table input using the helper function
            panel_text_list = []
            combined_db_schema, combined_db_schema_tbl, combined_db_schema_tbl_col = process_components_and_merge_metadata(
                conn, tbl_list, panel, include_dtype=self.include_dtype, panel_text_list=panel_text_list
            )
            
            # Update panel_text with results
            panel_text += "".join(panel_text_list)
            self.window.run_command("show_panel", {"panel": "output.meta_add"})

            # Check if any metadata was collected
            if not combined_db_schema:
                panel.run_command(
                    "append", {"characters": "No metadata collected. Please check your inputs.\n"}
                )
                panel.set_read_only(True)
                return

            panel.set_read_only(True)

            # Prompt for connection group name
            input_panel = self.window.show_input_panel(
                "Enter Connection Group Name: ",
                "",
                on_execute,
                None,
                None,
            )
            

        t1 = threading.Thread(
            target=main_func,
            args=[self, tbl_to_pull],
            name="meta_add",
        )
        t2 = create_timeout_monitor_thread(self.window, t1, timeout=180, thread_name="meta_timeout")
        t1.start()
        t2.start()


class MetaSelectConnection(sublime_plugin.WindowCommand):
    def run(self):
        # Get list of folders in DBMS directory
        dbms_path = get_dbms_path()
        folder_lst = []
        folder_names = []
        for item in os.listdir(dbms_path):
            item_path = os.path.join(dbms_path, item)
            if os.path.isdir(item_path):
                description_path = os.path.join(item_path, "description.txt")
                try:
                    with open(description_path, "r") as f:
                        description = f.read().strip()
                    folder_lst.append([item, description])
                except FileNotFoundError:
                    folder_lst.append([item, "No description available"])
                folder_names.append(item)
        
        self.folder_names = folder_names
        self.window.show_quick_panel(folder_lst, self.on_done, 0, 0)
    
    def on_done(self, index):
        if index == -1:
            return
        
        selected_folder = self.folder_names[index]
        
        # Update current_selection in settings
        try:
            update_settings("current_selection", selected_folder)
        except Exception as e:
            sublime.message_dialog(f"Error updating settings: {str(e)}")


class MetaUpdateConnectionGroup(MetaSelectConnection):
    def run(self, include_dtype="true"):
        self.include_dtype = include_dtype.lower() == "true"
        super().run()
    
    def on_done(self, index):
        if index == -1:
            return
        
        select = self.folder_names[index]
        connection_group_folder = os.path.join(get_dbms_path(), select)
        component_file_path = os.path.join(connection_group_folder, "conn-group-component.txt")
        
        # Read the component file
        try:
            with open(component_file_path, "r") as f:
                components = f.read().strip().split('\n')
        except FileNotFoundError:
            sublime.message_dialog(f"Component file not found for connection group '{select}'")
            return
        
        # Clean up the component list
        components = [
            comp.strip().lower()
            for comp in components
            if comp.strip() not in ["", " ", "\n", "\t"]
        ]
        
        if not components:
            sublime.message_dialog(f"No components found for connection group '{select}'")
            return

        def main_func(self, components, select, connection_group_folder):
            conn = ConnectorODBC()
            panel = self.window.create_output_panel("meta_update")
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)
            
            panel.run_command(
                "append", {"characters": f"Updating metadata for connection group '{select}'...\n"}
            )
            self.window.run_command("show_panel", {"panel": "output.meta_update"})

            # Process each component using the helper function
            combined_db_schema, combined_db_schema_tbl, combined_db_schema_tbl_col = process_components_and_merge_metadata(
                conn, components, panel, include_dtype=self.include_dtype
            )
            self.window.run_command("show_panel", {"panel": "output.meta_update"})

            # Check if any metadata was collected
            if not combined_db_schema:
                panel.run_command(
                    "append", {"characters": "No metadata collected. Please check your components.\n"}
                )
                panel.set_read_only(True)
                return

            # Recreate all metadata files
            db_list = list(combined_db_schema.keys())
            drop_down_list = create_drop_down_list(combined_db_schema_tbl_col)
            create_metadata_files(
                connection_group_folder, 
                db_list, 
                combined_db_schema, 
                combined_db_schema_tbl, 
                combined_db_schema_tbl_col, 
                drop_down_list,
                group_name=select
            )
            
            # Print summary
            print_metadata_summary(panel, connection_group_folder, db_list, drop_down_list)
            panel.set_read_only(True)
            
            # Reselect the connection to refresh autocomplete
            self.window.run_command("meta_select_connection")
            
            sublime.message_dialog(
                f"Successfully updated connection group '{select}' with {len(drop_down_list)} columns!"
            )

        t1 = threading.Thread(
            target=main_func,
            args=[self, components, select, connection_group_folder],
            name="meta_update",
        )
        t2 = create_timeout_monitor_thread(self.window, t1, timeout=360, thread_name="meta_update_timeout")
        t1.start()
        t2.start()


class MetaAddTableInConnGroup(MetaSelectConnection):
    def run(self, include_dtype="true"):
        self.include_dtype = include_dtype.lower() == "true"
        super().run()
    
    def on_done(self, index):
        if index == -1:
            return
        
        # Set the selected connection group folder
        self.folder = self.folder_names[index]
        self.connection_group_folder = os.path.join(get_dbms_path(), self.folder)
        
        # Show input panel for table to add
        input_panel = self.window.show_input_panel(
            "Enter table to add (format: db.schema.table): ",
            "",
            self.on_done2,
            None,
            None,
        )
    
    def on_done2(self, table_to_add):
        if not table_to_add.strip():
            return
            
        table_to_add = table_to_add.strip().lower()
        
        # Validate table format
        if table_to_add.count('.') != 2:
            sublime.message_dialog("Invalid table format. Please use: db.schema.table")
            return
        
        try:
            # 1. Read db-schema-tbl.json under self.folder
            db_schema_tbl_path = os.path.join(self.connection_group_folder, "db-schema-tbl.json")
            with open(db_schema_tbl_path, "r") as f:
                existing_db_schema_tbl = json.loads(f.read())

            
            # 2. Flatten all existing tables and check if table_to_add is already included
            existing_tables = []
            for db, schemas in existing_db_schema_tbl.items():
                for schema, tables in schemas.items():
                    for table in tables.keys():
                        existing_tables.append(f"{db}.{schema}.{table}")
            
            # Check if table already exists
            table_exists = table_to_add in existing_tables
            if table_exists:
                result = sublime.yes_no_cancel_dialog(
                    f"Table '{table_to_add}' already exists in connection group '{self.folder}'.\n"
                    "Do you want to refresh its metadata?",
                    "Refresh", "Cancel"
                )
                if result != sublime.DIALOG_YES:
                    return
            
            # Get metadata using get_meta_under_table
            if credential_set(show_msg=False) is False:
                sublime.message_dialog(
                    "Teradata username or password not setup\nUse ctrl+e,ctrl+p to setup"
                )
                return
            
            conn = ConnectorODBC()
            panel = self.window.create_output_panel("meta_add_table")
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)
            
            panel.run_command(
                "append", {"characters": f"Getting metadata for table: {table_to_add}\n"}
            )
            self.window.run_command("show_panel", {"panel": "output.meta_add_table"})
            
            try:
                db_list, db_schema, db_schema_tbl, db_schema_tbl_col = conn.get_meta_under_table(
                    table_to_add, include_dtype=self.include_dtype
                )
            except Exception as e:
                panel.run_command(
                    "append", {"characters": f"Error getting metadata: {str(e)}\n"}
                )
                sublime.message_dialog(f"Error getting metadata for table '{table_to_add}': {str(e)}")
                return
            
            if not db_schema_tbl:
                panel.run_command(
                    "append", {"characters": f"No metadata found for table: {table_to_add}\n"}
                )
                sublime.message_dialog(f"No metadata found for table: {table_to_add}")
                return
            
            panel.run_command(
                "append", {"characters": f"Successfully retrieved metadata for {table_to_add}\n"}
            )
            
            # 3. Compare and merge with existing JSON files
            
            # Read existing files
            db_list_path = os.path.join(self.connection_group_folder, "db-list.json")
            db_schema_path = os.path.join(self.connection_group_folder, "db-schema.json")
            db_schema_tbl_col_path = os.path.join(self.connection_group_folder, "db-schema-tbl-col.json")
            
            with open(db_list_path, "r") as f:
                existing_db_list = json.loads(f.read())
            with open(db_schema_path, "r") as f:
                existing_db_schema = json.loads(f.read())
            with open(db_schema_tbl_col_path, "r") as f:
                existing_db_schema_tbl_col = json.loads(f.read())
            
            # Merge db_list
            for db in db_list:
                if db not in existing_db_list:
                    existing_db_list.append(db)
            
            # Merge db_schema
            for db, schemas in db_schema.items():
                if db not in existing_db_schema:
                    existing_db_schema[db] = {}
                for schema, schema_info in schemas.items():
                    if schema not in existing_db_schema[db]:
                        existing_db_schema[db][schema] = schema_info
            
            # Merge db_schema_tbl
            for db, schemas in db_schema_tbl.items():
                if db not in existing_db_schema_tbl:
                    existing_db_schema_tbl[db] = {}
                for schema, tables in schemas.items():
                    if schema not in existing_db_schema_tbl[db]:
                        existing_db_schema_tbl[db][schema] = {}
                    for table, table_info in tables.items():
                        existing_db_schema_tbl[db][schema][table] = table_info
            
            # 4. Overwrite db-schema-tbl-col where part matched
            for db, schemas in db_schema_tbl_col.items():
                if db not in existing_db_schema_tbl_col:
                    existing_db_schema_tbl_col[db] = {}
                for schema, tables in schemas.items():
                    if schema not in existing_db_schema_tbl_col[db]:
                        existing_db_schema_tbl_col[db][schema] = {}
                    for table, columns in tables.items():
                        existing_db_schema_tbl_col[db][schema][table] = columns
            
            # 5. Update conn-group-component.txt if table doesn't exist
            component_file_path = os.path.join(self.connection_group_folder, "conn-group-component.txt")
            try:
                with open(component_file_path, "r") as f:
                    components = f.read().strip().split('\n')
                components = [comp.strip() for comp in components if comp.strip()]
            except FileNotFoundError:
                components = []
            
            if table_to_add not in components:
                components.append(table_to_add)
                with open(component_file_path, "w") as f:
                    f.write('\n'.join(components))
            
            # 6. Update drop-down.txt by overwriting that table's columns
            drop_down_path = os.path.join(self.connection_group_folder, "drop-down.txt")
            try:
                with open(drop_down_path, "r") as f:
                    existing_lines = f.read().strip().split('\n')
            except FileNotFoundError:
                existing_lines = []
            
            # Remove existing columns for this table
            table_prefix = f"{table_to_add}."
            filtered_lines = [line for line in existing_lines if not line.startswith(table_prefix)]
            
            # Add new columns for this table
            new_columns = []
            for db, schemas in db_schema_tbl_col.items():
                for schema, tables in schemas.items():
                    for table, columns in tables.items():
                        for column in columns.keys():
                            new_columns.append(f"{db}.{schema}.{table}.{column}")
            
            # Combine and sort
            all_lines = filtered_lines + new_columns
            all_lines = [line for line in all_lines if line.strip()]
            all_lines = sorted(list(set(all_lines)))  # Remove duplicates and sort
            
            # Write all updated files
            with open(db_list_path, "w") as f:
                json.dump(existing_db_list, f)
            
            with open(db_schema_path, "w") as f:
                json.dump(existing_db_schema, f)
            
            with open(db_schema_tbl_path, "w") as f:
                json.dump(existing_db_schema_tbl, f)
            
            with open(db_schema_tbl_col_path, "w") as f:
                json.dump(existing_db_schema_tbl_col, f)
            
            with open(drop_down_path, "w") as f:
                f.write('\n'.join(all_lines))
            
            # Update description.txt
            db_list_str = " , ".join(existing_db_list)
            column_count = len(all_lines)
            description_msg = f"Completions for DB `{db_list_str}`, {column_count} columns in total"
            description_path = os.path.join(self.connection_group_folder, "description.txt")
            with open(description_path, "w") as f:
                f.write(description_msg)
            
            panel.run_command(
                "append", {"characters": f"Successfully updated connection group '{self.folder}'\n"}
            )
            panel.set_read_only(True)
            
            # Refresh autocomplete selection
            self.window.run_command("meta_select_connection")
            
            action_word = "refreshed" if table_exists else "added"
            sublime.message_dialog(
                f"Table '{table_to_add}' has been successfully {action_word} in connection group '{self.folder}'"
            )
            
        except Exception as e:
            sublime.message_dialog(f"Error adding table: {str(e)}")


class MetaDeleteConnection(MetaSelectConnection):
    def on_done(self, index):
        if index == -1:
            return

        select = self.folder_names[index]
        connection_group_folder = os.path.join(get_dbms_path(), select)

        # Remove the connection group folder
        shutil.rmtree(connection_group_folder)

        self.window.run_command("meta_select_connection")





class MetaBrowseConnection(sublime_plugin.TextCommand):
    def run(self, edit):
        # 1. Read current_selection from settings
        current_selection = load_settings(get_cur_selection_only=True)
        
        # 2. Open current_selection folder under DBMS folder
        dbms_path = get_dbms_path()
        current_folder_path = os.path.join(dbms_path, current_selection)
        
        # 3. Read drop-down.txt and split by newline, clean up empty strings
        drop_down_file_path = os.path.join(current_folder_path, "drop-down.txt")
        with open(drop_down_file_path, "r") as f:
            file_content = f.read()
        
        # Split by newline and filter out empty strings, spaces, and newlines
        col_lst = [
            line.strip() for line in file_content.split("\n") 
            if line.strip() not in ["", " ", "\n"]
        ]
        col_lst = sorted(col_lst)
        
        self.col_lst = col_lst
        
        # 4. Show quick panel
        self.view.window().show_quick_panel(self.col_lst, self.on_done, 0, 0)

    def on_done(self, index):
        if index == -1:
            return
        
        # 1. Split user selection by "." to parse db.schema.table.col
        select = self.col_lst[index]
        parts = select.split(".")
        
        if len(parts) == 4:
            db, schema, table, col = parts
            # Generate SQL query: select a.col from db.schema.table
            txt = f"select a.{col} from {db}.{schema}.{table} as a;"
        else:
            # Fallback for different formats
            txt = f"-- Invalid format: {select}"
        
        # 2. Insert the query at cursor position
        cur = self.view.sel()[0].begin() + 10 + len(col) if len(parts) == 4 else self.view.sel()[0].begin()
        self.view.run_command("insert", {"characters": txt})
        self.view.sel().clear()
        self.view.sel().add(cur)


class MetaImportLocalConnection(sublime_plugin.WindowCommand):
    def run(self):
        # Ask user to select a folder
        sublime.select_folder_dialog(self.print_path)

    def print_path(self, path):
        if not path:
            return
            
        self.source_path = path
        # Get the folder name from the path
        folder_name = os.path.basename(path)
        
        # Check if folder already exists in DBMS folder
        dbms_path = get_dbms_path()
        destination_path = os.path.join(dbms_path, folder_name)
        if os.path.exists(destination_path):
            sublime.message_dialog(
                f"Connection group '{folder_name}' already exists in metastore. Please choose a different folder or rename the existing one."
            )
            return
        
        # Copy everything from source folder to DBMS folder
        try:
            shutil.copytree(self.source_path, destination_path)
        except Exception as e:
            sublime.message_dialog(f"Error copying folder: {str(e)}")
            return
        
        # Update settings current_selection
        try:
            update_settings("current_selection", folder_name)
        except Exception as e:
            sublime.message_dialog(f"Error updating settings: {str(e)}")
            return

        # Run meta_select_connection to refresh the selection
        self.window.run_command("meta_select_connection")
        
        sublime.message_dialog(
            f"Successfully imported connection group '{folder_name}' and set as current selection!"
        )


class MetaRemoveTableInConnGroup(MetaSelectConnection):
    def on_done(self, index):
        if index == -1:
            return

        # Get selected connection group folder name
        select = self.folder_names[index]
        connection_group_folder = os.path.join(get_dbms_path(), select)
        
        # Read db-schema-tbl.json
        db_schema_tbl_path = os.path.join(connection_group_folder, "db-schema-tbl.json")
        try:
            with open(db_schema_tbl_path, "r") as f:
                db_schema_tbl = json.loads(f.read())
        except FileNotFoundError:
            sublime.message_dialog(f"db-schema-tbl.json not found for connection group '{select}'")
            return

        # Flatten all tables from db_schema_tbl
        to_show = []
        for db, schemas in db_schema_tbl.items():
            for schema, tables in schemas.items():
                for table in tables.keys():
                    to_show.append(f"{db}.{schema}.{table}")

        if not to_show:
            sublime.message_dialog(f"No tables found in connection group '{select}'")
            return

        self.tbls = to_show
        self.connection_group_folder = connection_group_folder
        self.select = select

        self.window.show_quick_panel(
            to_show,
            self.on_done2,
            0,
            0,
            placeholder=f"Please Select Table You want to remove from `{select}`",
        )

    def on_done2(self, index):
        if index == -1:
            return

        # Parse selected table
        remove = self.tbls[index]
        parts = remove.split(".")
        if len(parts) != 3:
            sublime.message_dialog(f"Invalid table format: {remove}")
            return
        
        db, schema, table = parts

        try:
            # 1. Remove table from db-schema-tbl.json
            db_schema_tbl_path = os.path.join(self.connection_group_folder, "db-schema-tbl.json")
            with open(db_schema_tbl_path, "r") as f:
                db_schema_tbl = json.loads(f.read())
            
            if db in db_schema_tbl and schema in db_schema_tbl[db] and table in db_schema_tbl[db][schema]:
                del db_schema_tbl[db][schema][table]
                
                # Remove schema if empty
                if not db_schema_tbl[db][schema]:
                    del db_schema_tbl[db][schema]
                    
                    # Remove db if empty
                    if not db_schema_tbl[db]:
                        del db_schema_tbl[db]

            # 2. Remove columns from db-schema-tbl-col.json
            db_schema_tbl_col_path = os.path.join(self.connection_group_folder, "db-schema-tbl-col.json")
            with open(db_schema_tbl_col_path, "r") as f:
                db_schema_tbl_col = json.loads(f.read())
            
            if db in db_schema_tbl_col and schema in db_schema_tbl_col[db] and table in db_schema_tbl_col[db][schema]:
                del db_schema_tbl_col[db][schema][table]
                
                # Remove schema if empty
                if not db_schema_tbl_col[db][schema]:
                    del db_schema_tbl_col[db][schema]
                    
                    # Remove db if empty
                    if not db_schema_tbl_col[db]:
                        del db_schema_tbl_col[db]

            # 3. Update db-schema.json (remove schema if no tables left)
            db_schema_path = os.path.join(self.connection_group_folder, "db-schema.json")
            with open(db_schema_path, "r") as f:
                db_schema = json.loads(f.read())
            
            if db in db_schema and schema in db_schema[db]:
                # Check if schema has any tables left in db_schema_tbl
                if db not in db_schema_tbl or schema not in db_schema_tbl[db]:
                    del db_schema[db][schema]
                    
                    # Remove db if empty
                    if not db_schema[db]:
                        del db_schema[db]

            # 4. Update db-list.json (remove db if no schemas left)
            db_list_path = os.path.join(self.connection_group_folder, "db-list.json")
            with open(db_list_path, "r") as f:
                db_list = json.loads(f.read())
            
            if db not in db_schema:
                if db in db_list:
                    db_list.remove(db)

            # 5. Update conn-group-component.txt (remove table if exists)
            component_file_path = os.path.join(self.connection_group_folder, "conn-group-component.txt")
            try:
                with open(component_file_path, "r") as f:
                    components = f.read().strip().split('\n')
                
                # Remove the table if it exists in components
                table_entry = f"{db}.{schema}.{table}"
                if table_entry in components:
                    components.remove(table_entry)
                
                # Write back updated components
                with open(component_file_path, "w") as f:
                    f.write('\n'.join(components))
            except FileNotFoundError:
                pass  # File might not exist for older connection groups

            # 6. Update drop-down.txt (remove all columns for the table)
            drop_down_path = os.path.join(self.connection_group_folder, "drop-down.txt")
            try:
                with open(drop_down_path, "r") as f:
                    lines = f.read().strip().split('\n')
                
                # Filter out lines that belong to the removed table
                table_prefix = f"{db}.{schema}.{table}."
                filtered_lines = [line for line in lines if not line.startswith(table_prefix)]
                
                # Write back filtered lines
                with open(drop_down_path, "w") as f:
                    f.write('\n'.join(filtered_lines))
            except FileNotFoundError:
                pass

            # Write all updated JSON files
            with open(db_schema_tbl_path, "w") as f:
                json.dump(db_schema_tbl, f)
            
            with open(db_schema_tbl_col_path, "w") as f:
                json.dump(db_schema_tbl_col, f)
            
            with open(db_schema_path, "w") as f:
                json.dump(db_schema, f)
            
            with open(db_list_path, "w") as f:
                json.dump(db_list, f)

            # Update description.txt
            db_list_str = " , ".join(db_list) if db_list else "No databases"
            
            # Count remaining columns for description
            column_count = 0
            for drop_line in filtered_lines:
                if drop_line.strip():
                    column_count += 1
            
            description_msg = f"Completions for DB `{db_list_str}`, {column_count} columns in total"
            description_path = os.path.join(self.connection_group_folder, "description.txt")
            with open(description_path, "w") as f:
                f.write(description_msg)

            # Reselect connection to refresh autocomplete
            self.window.run_command("meta_select_connection")
            
            sublime.message_dialog(
                f"Table `{remove}` has been successfully removed from connection group `{self.select}`"
            )

        except Exception as e:
            sublime.message_dialog(f"Error removing table: {str(e)}")


# Helper functions for common metadata operations
def process_components_and_merge_metadata(conn, components, panel, include_dtype=True, panel_text_list=None):
    """Process a list of components and merge their metadata into combined structures"""
    combined_db_schema = {}
    combined_db_schema_tbl = {}
    combined_db_schema_tbl_col = {}
    
    for comp in components:
        try:
            dot_count = comp.count('.')
            
            if dot_count == 2:
                # db.schema.table format
                panel.run_command(
                    "append", {"characters": f"Processing table: {comp}\n"}
                )
                _, db_schema, db_schema_tbl, db_schema_tbl_col = conn.get_meta_under_table(comp, include_dtype=include_dtype)
            elif dot_count == 1:
                # db.schema format
                panel.run_command(
                    "append", {"characters": f"Processing schema: {comp}\n"}
                )
                _, db_schema, db_schema_tbl, db_schema_tbl_col = conn.get_meta_under_schema(comp, include_dtype=include_dtype)
            elif dot_count == 0:
                # db format
                panel.run_command(
                    "append", {"characters": f"Processing database: {comp}\n"}
                )
                _, db_schema, db_schema_tbl, db_schema_tbl_col = conn.get_meta_under_db(comp, include_dtype=include_dtype)
            else:
                panel.run_command(
                    "append", {"characters": f"Invalid format: {comp} (use db, db.schema or db.schema.table)\n"}
                )
                if panel_text_list is not None:
                    panel_text_list.append(f"Invalid format: {comp} (use db, db.schema or db.schema.table)\n")
                continue

            # Check if metadata was found
            if not db_schema:
                panel.run_command(
                    "append", {"characters": f"{comp} not found or no accessible metadata\n"}
                )
                if panel_text_list is not None:
                    panel_text_list.append(f"{comp} not found or no accessible metadata\n")
            else:
                # Merge metadata into combined structures
                for db, schemas in db_schema.items():
                    if db not in combined_db_schema:
                        combined_db_schema[db] = {}
                    combined_db_schema[db].update(schemas)
                
                for db, schemas in db_schema_tbl.items():
                    if db not in combined_db_schema_tbl:
                        combined_db_schema_tbl[db] = {}
                    for schema, tables in schemas.items():
                        if schema not in combined_db_schema_tbl[db]:
                            combined_db_schema_tbl[db][schema] = {}
                        combined_db_schema_tbl[db][schema].update(tables)
                
                for db, schemas in db_schema_tbl_col.items():
                    if db not in combined_db_schema_tbl_col:
                        combined_db_schema_tbl_col[db] = {}
                    for schema, tables in schemas.items():
                        if schema not in combined_db_schema_tbl_col[db]:
                            combined_db_schema_tbl_col[db][schema] = {}
                        combined_db_schema_tbl_col[db][schema].update(tables)

                panel.run_command(
                    "append",
                    {"characters": f"Successfully added {comp} to metadata\n"},
                )
                if panel_text_list is not None:
                    panel_text_list.append(f"Successfully added {comp} to metadata\n")
                    
        except Exception as e:
            panel.run_command(
                "append", {"characters": f"Error processing {comp}: {str(e)}\n"}
            )
            if panel_text_list is not None:
                panel_text_list.append(f"Error processing {comp}: {str(e)}\n")
    
    return combined_db_schema, combined_db_schema_tbl, combined_db_schema_tbl_col


def create_metadata_folder(folder_path, folder_name, panel=None):
    """Create or recreate a metadata folder"""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        if panel:
            panel.run_command(
                "append",
                {"characters": f"Removed existing '{folder_name}' folder\n"},
            )
    
    os.makedirs(folder_path, exist_ok=True)
    if panel:
        panel.run_command(
            "append",
            {"characters": f"Created '{folder_name}' folder structure\n"},
        )


def create_drop_down_list(db_schema_tbl_col):
    """Create flattened column list from db_schema_tbl_col structure"""
    drop_down_set = set()
    for db, schemas in db_schema_tbl_col.items():
        for schema, tables in schemas.items():
            for table, columns in tables.items():
                for column in columns.keys():
                    drop_down_set.add(f"{db}.{schema}.{table}.{column}")
    return list(drop_down_set)


def create_metadata_files(folder_path, db_list, db_schema, db_schema_tbl, db_schema_tbl_col, drop_down_list, group_name=None):
    """Create all standard metadata JSON files in the specified folder"""
    # Create db-list.json
    with open(os.path.join(folder_path, "db-list.json"), "w") as f:
        f.write(json.dumps(db_list))
    
    # Create db-schema.json
    with open(os.path.join(folder_path, "db-schema.json"), "w") as f:
        f.write(json.dumps(db_schema))
    
    # Create db-schema-tbl.json
    with open(os.path.join(folder_path, "db-schema-tbl.json"), "w") as f:
        f.write(json.dumps(db_schema_tbl))
    
    # Create db-schema-tbl-col.json
    with open(os.path.join(folder_path, "db-schema-tbl-col.json"), "w") as f:
        f.write(json.dumps(db_schema_tbl_col))
    
    # Create drop-down.txt (flattened column list)
    with open(os.path.join(folder_path, "drop-down.txt"), "w") as f:
        f.write("\n".join(drop_down_list))
    
    # Create description.txt
    db_list_str = " , ".join(db_list)
    description_msg = f"Completions for DB `{db_list_str}`, {len(drop_down_list)} columns in total"
    
    with open(os.path.join(folder_path, "description.txt"), "w") as f:
        f.write(description_msg)


def create_conn_group_component(folder_path, components):
    """Create conn-group-component.txt file with user input components"""
    component_file_path = os.path.join(folder_path, "conn-group-component.txt")
    
        # Multiple components, join with newlines
    content = "\n".join(components)
 
    
    with open(component_file_path, "w") as f:
        f.write(content)


def print_metadata_summary(panel, folder_path, db_list, drop_down_list, additional_files=None):
    """Print summary of created metadata files to panel"""
    summary_text = f"\nFinished creating metadata files:\n"
    summary_text += f"- {os.path.join(folder_path, 'db-list.json')} ({len(db_list)} databases)\n"
    summary_text += f"- {os.path.join(folder_path, 'db-schema.json')}\n"
    summary_text += f"- {os.path.join(folder_path, 'db-schema-tbl.json')}\n"
    summary_text += f"- {os.path.join(folder_path, 'db-schema-tbl-col.json')}\n"
    summary_text += f"- {os.path.join(folder_path, 'drop-down.txt')} ({len(drop_down_list)} columns)\n"
    summary_text += f"- {os.path.join(folder_path, 'description.txt')}\n"
    summary_text += f"- {os.path.join(folder_path, 'conn-group-component.txt')}\n"
    
    if additional_files:
        for file_path in additional_files:
            summary_text += f"- {file_path}\n"
    
    panel.run_command("append", {"characters": summary_text})


def create_timeout_monitor_thread(window, main_thread, timeout=180, thread_name="meta_timeout"):
    """Create a timeout monitoring thread"""
    def print_status_msg(window, t1, timeout):
        duration = 0
        while t1.is_alive() and duration < timeout:
            time.sleep(1)
            sublime.status_message(
                f"Building autocomplete metadata for {duration} seconds..."
            )
            duration += 1
        if duration >= timeout:
            stop_thread(t1)
            panel = window.create_output_panel("timeout")
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)
            panel.run_command(
                "insert",
                {
                    "characters": f"Execution timeout after {timeout} seconds, thread_number {t1.native_id}.\nCheck VPN or increase timeout in key binding args for run_sql_cmd"
                },
            )
            panel.set_read_only(True)
            window.run_command("show_panel", {"panel": "output.timeout"})

    return threading.Thread(
        target=print_status_msg,
        args=[window, main_thread, timeout],
        name=thread_name,
    )
