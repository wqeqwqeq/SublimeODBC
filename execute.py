import sublime
import sublime_plugin
import os
import json
import threading
import time
import ctypes
import csv


from SQLAPI.util import load_package_path, credential_set,load_settings
from SQLAPI.connect import ConnectorODBC
from tabulate import tabulate
import sqlparse


# Global paths
cache_path, lib_path, project_path, metastore_path = load_package_path()
# Global connection object
conn = None

# Global thread tracking for SQL operations
active_sql_threads = {}

print(os.getcwd())

class SoStartConn(sublime_plugin.WindowCommand):
    def run(self):
        """Initialize ODBC connection when command is triggered"""
        global conn
        
        # Check if environment variables are set
        if credential_set(show_msg=False):
            if conn is not None:
                sublime.status_message("ODBC connection already established")
                return
            
            # Start connection in a separate thread
            t1 = threading.Thread(
                target=self.get_connect,
                name="odbc_connect",
            )
            t2 = threading.Thread(
                target=self.conn_timeout,
                args=[t1, 15],
                name="odbc_timeout_query",
            )
            t1.start()
            t2.start()
            
            sublime.status_message("Starting ODBC connection...")
        else:
            settings = load_settings()
            current_dbms = settings.get("current_dbms", "")
            sublime.message_dialog(f"Default DBMS is {current_dbms}\n{current_dbms} Username or password not setup\nSelect DBMS to set up username and password")
            self.window.run_command("meta_password")

    def get_connect(self):
        """Establish connection to database"""
        try:
            global conn
            conn = ConnectorODBC() 
            sublime.status_message(f"ODBC connection established")
            print(f"Detected username and pw, Conn is set , {conn} ")
        finally:
            pass

    def conn_timeout(self, t1, timeout):
        """Handle connection timeout"""
        duration = 0
        while t1.is_alive() and duration < timeout:
            time.sleep(1)
            duration += 1
        if duration >= timeout:
            thread_id = t1.native_id
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                thread_id, ctypes.py_object(SystemExit)
            )
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print("Exception raise failure")
            print(f"Successfull stop thread {thread_id}")
            sublime.message_dialog(
                f"Connect to Server timeout in {timeout} seconds, please check if server is running"
            )
    


def load_cache_dict(cache_path):
    try:
        with open(cache_path, "r") as f:
            file = f.read()
    except FileNotFoundError:
        with open(cache_path, "w") as f:
            f.write("{}")
        with open(cache_path, "r") as f:
            file = f.read()
    return json.loads(file)


def add_result_to_cache(cache_dict, result, number_of_cache_query):
    if len(cache_dict) < number_of_cache_query:
        cache_dict.update(result)
        return cache_dict
    else:
        cache_dict.pop(list(cache_dict.keys())[0])
        cache_dict.update(result)
        return cache_dict


def stop_thread_safely(thread_obj, thread_name="Unknown"):
    """Safely stop a thread by setting a stop flag and optionally using thread termination as last resort"""
    if not thread_obj or not thread_obj.is_alive():
        print(f"Thread {thread_name} is not running")
        return False
    
    thread_id = thread_obj.native_id
    print(f"Attempting to stop thread {thread_name} (ID: {thread_id})")
    
    # Try graceful termination first by removing from active threads
    # This signals the thread to stop on its next check
    if thread_id in active_sql_threads:
        active_sql_threads[thread_id]['stop_requested'] = True
        print(f"Stop signal sent to thread {thread_name}")
    
    # Wait a bit for graceful shutdown
    thread_obj.join(timeout=2.0)
    
    if thread_obj.is_alive():
        # If still alive, use the more aggressive approach as last resort
        print(f"Thread {thread_name} still alive, using forceful termination")
        try:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                thread_id, ctypes.py_object(SystemExit)
            )
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print("Exception raise failure")
                return False
            print(f"Forcefully stopped thread {thread_name}")
            return True
        except Exception as e:
            print(f"Failed to stop thread {thread_name}: {e}")
            return False
    else:
        print(f"Thread {thread_name} stopped gracefully")
        return True


def cancel_database_operations():
    """Cancel any running database operations"""
    global conn
    if conn is not None:
        try:
            # Try to cancel the current operation
            if hasattr(conn, 'cursor') and conn.cursor:
                try:
                    conn.cursor.cancel()
                    print("Database operation cancelled")
                except Exception as e:
                    print(f"Could not cancel database operation: {e}")
            
            # For some ODBC drivers, we might need to close and reconnect
            # This is handled by the connection restart functionality
        except Exception as e:
            print(f"Error during database operation cancellation: {e}")


# Legacy function for backward compatibility - now uses safer approach
def stop_thread(t1):
    """Legacy function - use stop_thread_safely instead"""
    if isinstance(t1, int):
        thread_id = t1
        # Find thread by ID
        thread_obj = None
        for tid, thread in threading._active.items():
            if thread.native_id == thread_id:
                thread_obj = thread
                break
        if thread_obj:
            return stop_thread_safely(thread_obj, f"Thread-{thread_id}")
    else:
        return stop_thread_safely(t1, getattr(t1, 'name', 'Unknown'))


class SoRunSqlCmd(sublime_plugin.WindowCommand):
    def run(self, limit, number_of_cache_query, timeout, output_in_panel, queries=None):
        # Check if connection is available
        if conn is not None:
            print(queries)
            t1 = threading.Thread(
                target=self._execute_sql_main,
                args=[limit, number_of_cache_query, queries, output_in_panel],
                name="sa_run_sql_cmd",
            )
            t2 = threading.Thread(
                target=self._print_status_msg,
                args=[t1, timeout],
                name=f"sa_timeout_query",
            )
            
            # Register threads in our tracking system
            self._register_thread(t1, "SQL Execution")
            self._register_thread(t2, "SQL Timeout Monitor")
            
            t1.start()
            t2.start()
        else:
            sublime.message_dialog(
                "Database connection not established. Please run 'Start Connection' command first."
            )

    def _register_thread(self, thread_obj, description):
        """Register a thread in the global tracking system"""
        global active_sql_threads
        active_sql_threads[thread_obj.native_id] = {
            'thread': thread_obj,
            'description': description,
            'stop_requested': False,
            'started_at': time.time()
        }

    def _execute_sql_main(self, limit, number_of_cache_query, queries, output_in_panel):
        """Main SQL execution logic"""
        current_thread_id = threading.current_thread().native_id
        
        try:
            view = self.window.active_view()
            queries = self._get_queries(view, queries)
            panel_name = self._get_panel_name(view)

            for query in queries:
                # Check if stop was requested
                if self._should_stop_execution(current_thread_id):
                    print("SQL execution stopped by user request")
                    break
                    
                if set(query) == {"\n"}:
                    continue
                
                parsed = sqlparse.parse(query)[0]
                has_limit, has_sample = self._check_query_limits(query, limit)
                
                panel = self._setup_output_panel(output_in_panel)
                
                # Handle cache logic and execution
                self._process_query(query, panel, has_limit, has_sample, limit, 
                                  number_of_cache_query, parsed, panel_name, output_in_panel)
                
                panel.set_read_only(True)
        finally:
            # Clean up thread registration
            self._unregister_thread(current_thread_id)

    def _should_stop_execution(self, thread_id):
        """Check if the current thread should stop execution"""
        global active_sql_threads
        if thread_id in active_sql_threads:
            return active_sql_threads[thread_id].get('stop_requested', False)
        return False

    def _unregister_thread(self, thread_id):
        """Remove thread from tracking system"""
        global active_sql_threads
        if thread_id in active_sql_threads:
            del active_sql_threads[thread_id]

    def _get_queries(self, view, queries):
        """Extract queries from view selection or parameter"""
        if queries is None:
            cursor = view.sel()[0]
            a, b = cursor.begin(), cursor.end()
            if a > b:
                a, b = b, a
            queries = view.substr(sublime.Region(a, b))
        return queries.split(";")

    def _get_panel_name(self, view):
        """Get the panel name from the view"""
        if view.file_name() is not None:
            panel_name = os.path.basename(view.file_name())
        else:
            panel_name = view.name()
        return panel_name if panel_name != "" else "untitled"

    def _check_query_limits(self, query, limit):
        """Check if query has limits or samples"""
        has_limit = bool(limit)
        has_sample = " top " in query.lower() or " sample " in query.lower()
        return has_limit, has_sample

    def _setup_output_panel(self, output_in_panel):
        """Setup output panel or new view for results"""
        if output_in_panel:
            return self.window.create_output_panel("result")
        else:
            panel = self._setup_new_view_for_output()
            panel.set_read_only(False)
            panel.settings().set("word_wrap", False)
            return panel

    def _setup_new_view_for_output(self):
        """Setup a new view for output in a split pane"""
        num_groups = self.window.num_groups()
        if num_groups <= 1:
            self.window.run_command("new_file")
            self.window.run_command("new_pane")
            self.window.set_layout({
                "cols": [0.0, 1.0],
                "rows": [0.0, 0.55, 1.0],
                "cells": [[0, 0, 1, 1], [0, 1, 1, 2]],
            })
            self.window.focus_group(1)
        else:
            if num_groups > 1:
                self.window.focus_group(1)
            self.window.run_command("new_file")

        view_name = self._generate_unique_view_name()
        panel = self.window.active_view()
        panel.set_name(view_name)
        panel.set_scratch(True)
        return panel

    def _generate_unique_view_name(self):
        """Generate a unique name for query result views"""
        all_views_name = [view.name() for view in self.window.views()]
        all_result = [
            i.split("Query Result")[1].strip()
            for i in all_views_name
            if "Query Result" in i
        ]
        
        if len(all_result) == 0:
            return "Query Result 0"
        else:
            result_idx = []
            for i in all_result:
                try:
                    result_idx.append(int(i))
                except:
                    pass
            max_idx = max(result_idx) + 1 if result_idx else 0
            return f"Query Result {max_idx}"

    def _process_query(self, query, panel, has_limit, has_sample, limit,
                      number_of_cache_query, parsed, panel_name, output_in_panel):
        """Process a single query - check cache, execute, and display results"""
        # Check cache first
        cache_dict = load_cache_dict(cache_path)
        cached_result = cache_dict.get(query)
        
        if cached_result is not None:
            self._display_cached_result(panel, cached_result, cache_dict, number_of_cache_query)
        else:
            self._execute_and_display_query(query, panel, has_limit, has_sample, limit,
                                           number_of_cache_query, parsed, cache_dict)
        
        # Show results
        if output_in_panel:
            self.window.run_command("show_panel", {"panel": "output.result"})
        else:
            self._append_query_info(panel, query, panel_name)

    def _display_cached_result(self, panel, cached_result, cache_dict, number_of_cache_query):
        """Display results from cache"""
        panel.run_command("append", {"characters": f"{cached_result}"})
        panel.run_command("append", {"characters": "\n\n\nReturn from Cache"})
        panel.run_command("append", {
            "characters": f"\n{len(cache_dict)}/{number_of_cache_query}  (num of query in cache vs maxium cache)"
        })

    def _execute_and_display_query(self, query, panel, has_limit, has_sample, limit,
                                  number_of_cache_query, parsed, cache_dict):
        """Execute query and display results"""
        current_thread_id = threading.current_thread().native_id
        start = time.time()
        
        try:
            # Check if stop was requested before executing
            if self._should_stop_execution(current_thread_id):
                panel.run_command("append", {"characters": "Query execution cancelled by user"})
                return
                
            conn.execute(query)
            dur = time.time() - start
            print("query is ,", query)
            has_exec_error = False
        except Exception as e:
            error = e
            has_exec_error = True
            print(error)
            dur = time.time() - start

        if has_exec_error:
            self._display_error(panel, str(error))
        else:
            self._handle_successful_execution(query, panel, has_limit, has_sample, limit,
                                            number_of_cache_query, parsed, cache_dict, dur)

    def _handle_successful_execution(self, query, panel, has_limit, has_sample, limit,
                                   number_of_cache_query, parsed, cache_dict, dur):
        """Handle successful query execution"""
        rowcount = conn.cursor.rowcount
        
        try:
            if has_sample or not has_limit:
                result = conn.cursor.fetchall()
            else:
                result = conn.cursor.fetchmany(limit)
            
            self._display_query_results(query, panel, result, has_limit, has_sample, 
                                      limit, number_of_cache_query, cache_dict, dur, rowcount)
                                      
        except Exception as fetch_error:
            print(f"Fetch error: {fetch_error}")
            self._display_non_select_result(panel, parsed, dur, rowcount)

    def _display_query_results(self, query, panel, result, has_limit, has_sample,
                             limit, number_of_cache_query, cache_dict, dur, rowcount):
        """Display tabulated query results"""
        cols = [row[0] for row in conn.cursor.description]
        result2 = []
        for i in result:
            result2.append(tuple(
                j.replace("\n", " ") if isinstance(j, str) else j
                for j in i
            ))

        to_return = tabulate(result2, cols, "psql", disable_numparse=True)
        
        # Cache the result
        self._cache_result(query, to_return, cache_dict, number_of_cache_query)
        
        # Display results
        panel.run_command("append", {"characters": f"{to_return};"})
        panel.run_command("append", {
            "characters": f"\n\n\nActual Query retrieve time {round(dur,2)}, total rows retrieved are {rowcount}"
        })

        if has_limit and not has_sample and len(result) == limit:
            panel.run_command("append", {
                "characters": f"\nATTENTION! RESULT OMITTED!\nOnly showed {limit} out of {rowcount} rows, change limit under `sa_run_sql_cmd` in keybind or explicitly pass sample number"
            })

    def _display_non_select_result(self, panel, parsed, dur, rowcount):
        """Display results for non-SELECT statements"""
        if parsed.get_type() != "UNKNOWN":
            if rowcount == -1:
                to_return = f"Successfully run {parsed.get_type().lower()} statement in {round(dur,2)} seconds!"
            else:
                to_return = f"Successfully run {parsed.get_type().lower()} statement in {round(dur,2)} seconds!\n{rowcount} rows impacted "
        else:
            to_return = f"Successfully run statement in {round(dur,2)} seconds!"
        
        panel.run_command("append", {"characters": f"{to_return}"})

    def _display_error(self, panel, error_msg):
        """Display error message"""
        panel.run_command("append", {"characters": f"{error_msg}"})

    def _cache_result(self, query, result, cache_dict, number_of_cache_query):
        """Cache the query result"""
        new_cache = {query: result}
        cache_dict = add_result_to_cache(cache_dict, new_cache, number_of_cache_query)
        cache_dict_to_write = json.dumps(cache_dict)
        
        with open(cache_path, "w") as f:
            f.write(cache_dict_to_write)

    def _append_query_info(self, panel, query, panel_name):
        """Append query information to the panel"""
        query_run = f";\n\nQuery Executed;\n{query};\n"
        panel.run_command("append", {"characters": f"{query_run}"})
        panel.run_command("append", {"characters": f"\nQuery run from tab: `{panel_name}`"})

    def _print_status_msg(self, t1, timeout):
        """Print status messages during query execution"""
        duration = 0
        while t1.is_alive() and duration < timeout:
            time.sleep(1)
            sublime.status_message(f"Executing SQL query for {duration} seconds...")
            duration += 1
            
        if duration >= timeout:
            # Cancel database operations first
            cancel_database_operations()
            # Then stop the thread
            stop_thread_safely(t1, "SQL Execution (Timeout)")
            self._display_timeout_message(timeout, t1.native_id)
            # Clean up thread tracking
            self._unregister_thread(t1.native_id)
        
        # Always clean up timeout monitor thread
        current_thread_id = threading.current_thread().native_id
        self._unregister_thread(current_thread_id)

    def _display_timeout_message(self, timeout, thread_id):
        """Display timeout message in a message box"""
        sublime.message_dialog(
            f"Execution timeout after {timeout} seconds, thread_number {thread_id}.\nIncrease timeout in key binding args for so_run_sql_cmd"
        )


class SaClearCache(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            os.remove(cache_path)
            sublime.message_dialog("Dropped Cache Query Result")
        except:
            sublime.message_dialog("Cache is empty!")


class SaInterruptQuery(sublime_plugin.WindowCommand):
    def run(self):
        """Interrupt running SQL queries and threads effectively"""
        interrupted_threads = self._interrupt_sql_operations()
        self._display_interrupt_results(interrupted_threads)

    def _interrupt_sql_operations(self):
        """Cancel database operations and stop SQL-related threads"""
        global active_sql_threads
        interrupted_threads = []
        
        # First, cancel any running database operations
        try:
            cancel_database_operations()
        except Exception as e:
            print(f"Error canceling database operations: {e}")
        
        # Get all active SQL threads from our tracking system
        threads_to_stop = list(active_sql_threads.values())
        
        if not threads_to_stop:
            sublime.status_message("No active SQL operations to interrupt")
            return []
        
        # Stop each tracked thread
        for thread_info in threads_to_stop:
            thread_obj = thread_info['thread']
            description = thread_info['description']
            
            if thread_obj.is_alive():
                success = stop_thread_safely(thread_obj, description)
                interrupted_threads.append({
                    'name': thread_obj.name,
                    'id': thread_obj.native_id,
                    'description': description,
                    'success': success,
                    'runtime': time.time() - thread_info['started_at']
                })
        
        # Also check for any legacy threads that might not be in our tracking
        self._stop_legacy_threads(interrupted_threads)
        
        # Clear the tracking registry
        active_sql_threads.clear()
        
        return interrupted_threads

    def _stop_legacy_threads(self, interrupted_threads):
        """Stop any SQL-related threads not in our tracking system (legacy support)"""
        legacy_thread_names = [
            "sa_run_sql_cmd",
            "sa_timeout_query", 
            "odbc_connect",
            "odbc_timeout_query",
            "to_csv",
            "Transpose",
            "meta_init",
            "meta_timeout",
            "meta_add"
        ]
        
        # Find threads by name that are still running
        for tid, thread in threading._active.items():
            if (thread.name in legacy_thread_names and 
                thread.is_alive() and 
                not any(t['id'] == thread.native_id for t in interrupted_threads)):
                
                success = stop_thread_safely(thread, f"Legacy {thread.name}")
                interrupted_threads.append({
                    'name': thread.name,
                    'id': thread.native_id,
                    'description': f"Legacy thread: {thread.name}",
                    'success': success,
                    'runtime': 'Unknown'
                })

    def _display_interrupt_results(self, interrupted_threads):
        """Display the results of the interrupt operation"""
        panel = self.window.create_output_panel("interrupt")
        panel.set_read_only(False)
        panel.settings().set("word_wrap", False)
        
        if not interrupted_threads:
            panel.run_command("insert", {
                "characters": "No active SQL operations found to interrupt."
            })
        else:
            # Build summary
            successful = sum(1 for t in interrupted_threads if t['success'])
            total = len(interrupted_threads)
            
            summary = f"SQL Interrupt Summary: {successful}/{total} threads stopped successfully\n\n"
            
            # Add details for each thread
            for thread_info in interrupted_threads:
                status = "✓ Stopped" if thread_info['success'] else "✗ Failed"
                runtime = f"{thread_info['runtime']:.1f}s" if isinstance(thread_info['runtime'], (int, float)) else thread_info['runtime']
                
                details = (f"{status} | {thread_info['name']} (ID: {thread_info['id']})\n"
                          f"   Description: {thread_info['description']}\n"
                          f"   Runtime: {runtime}\n\n")
                summary += details
            
            # Add current thread status
            active_count = len([t for t in threading._active.values() 
                              if t.name in ["sa_run_sql_cmd", "sa_timeout_query", "odbc_connect", "odbc_timeout_query"]])
            summary += f"Remaining SQL threads: {active_count}"
            
            panel.run_command("insert", {"characters": summary})
        
        panel.set_read_only(True)
        self.window.run_command("show_panel", {"panel": "output.interrupt"})
        
        # Show status message
        if interrupted_threads:
            successful = sum(1 for t in interrupted_threads if t['success'])
            sublime.status_message(f"Interrupted {successful} SQL operations")
        else:
            sublime.status_message("No SQL operations to interrupt")




class SoRestartConnection(sublime_plugin.TextCommand):
    def run(self, edit):
        conn1 = str(conn)
        self.conn1 = conn1

        conn.close()
        self.restart()

    def restart(self):
        global conn
        conn = ConnectorODBC()
        conn2 = str(conn)
        sublime.message_dialog("Restarted connection!")
        print("Before:", self.conn1, "\n", "After:", conn2)


class SoTblToCsv(sublime_plugin.WindowCommand):
    def run(self, per_chunk=10000):
        def main(self, per_chunk):
            view = self.window.active_view()
            region = sublime.Region(0, view.size())
            content = view.substr(region)
            query = content.split("Query Executed;")[1].split("Query run from tab:")[0]
            self.window.focus_group(1)
            self.window.run_command("new_file")

            self.panel = self.window.active_view()
            self.panel.set_name("Export progress")
            self.panel.set_scratch(True)

            self.panel.run_command(
                "append", {"characters": f"Executing Query to export...\n {query}\n"}
            )
            start = time.time()
            conn.execute(query)
            end = time.time() - start
            self.panel.run_command(
                "append",
                {
                    "characters": f"Executing finished, time elapsed {round(end,2)} seconds\n\n"
                },
            )

            total = conn.cursor.rowcount
            boo = sublime.ok_cancel_dialog(
                msg=f"Total row count is {total}\n\n\nQuery Executed:\n {query}",
                ok_title="Lets Parse!",
                title="CSV Parse Confirm",
            )
            if not boo:
                print("No Parse")
                return
            start = time.time()
            final = []

            while True:
                chunk = conn.cursor.fetchmany(per_chunk)
                if len(chunk) == 0:
                    self.panel.run_command("append", {"characters": f"Fetch Done\n"})
                    break
                final += chunk
                total -= 10000
                self.panel.run_command(
                    "append",
                    {"characters": f"Fetched {per_chunk} rows,{total} rows to go\n"},
                )

            result2 = [list(i) for i in final]
            cols = [i[0] for i in conn.cursor.description]
            self.panel.run_command(
                "append",
                {
                    "characters": f"Time elapsed {round(time.time() - start,2)} seconds\n\n"
                },
            )

            self.cols = cols
            self.result2 = result2

            path = sublime.save_dialog(
                self.get_path,
                extension="csv",
                name="Sublime_Export",
                directory=f"/C/Users/{os.getlogin()}",
            )

        t1 = threading.Thread(
            target=main,
            args=[self, per_chunk],
            name="to_csv",
        )
        t1.start()

    def get_path(self, path):
        with open(path, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(self.cols)
            wr.writerows(self.result2)
            self.panel.run_command(
                "append",
                {"characters": f"CSV Exported at {path}"},
            )


class TblTranspose(sublime_plugin.WindowCommand):
    def run(self, limit=1000):
        def main(self):
            view = self.window.active_view()
            region = sublime.Region(0, view.size())
            content = view.substr(region)
            query = content.split("Query Executed;")[1].split("Query run from tab:")[0]
            file_name = self.window.active_view().name()
            self.window.focus_group(1)

            self.window.run_command("new_file")

            self.panel = self.window.active_view()
            self.panel.set_name(f"Transpose from {file_name}")
            self.panel.set_scratch(True)

            self.panel.run_command(
                "append", {"characters": f"Executing Query to transpose......;\n"}
            )
            start = time.time()
            conn.execute(query)
            end = time.time() - start

            if conn.cursor.rowcount >= limit:
                self.panel.run_command(
                    "append",
                    {
                        "characters": f"Number of rows in cursor is {conn.cursor.rowcount}, limit is {limit}\nTranspose rows out of bound!!! "
                    },
                )
                return

            lst = conn.cursor.fetchall()
            cols = [ele[0] for ele in conn.cursor.description]
            result2 = [ele for ele in zip(cols, *lst) if len(set(ele[1:])) != 1]
            l = len(lst)
            column = ["Column"] + [f"Row_{i}" for i in range(1, l + 1)]

            to_return = tabulate(result2, column, "psql", disable_numparse=True)
            self.panel.run_command(
                "append",
                {"characters": f"\n{to_return};\n\n"},
            )
            self.panel.run_command(
                "append",
                {
                    "characters": f"Executing finished, time elapsed {round(end,2)} seconds;\nQuery Executed:\n{query}\n\n"
                },
            )
            self.panel.set_read_only(True)

        t1 = threading.Thread(
            target=main,
            args=[self],
            name="Transpose",
        )
        t1.start()


class SoRemoveCacheFile(sublime_plugin.WindowCommand):
    def run(self):
        """Remove the cache query JSON file from the metastore folder"""
        try:
            # Get the cache file path from the global cache_path variable
            if os.path.exists(cache_path):
                os.remove(cache_path)
                sublime.status_message("Cache query file removed successfully")
            else:
                sublime.status_message("Cache query file does not exist")
        except Exception as e:
            sublime.error_message(f"Error removing cache file: {str(e)}")

