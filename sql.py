import sublime
import sublime_plugin
import os
import json
import threading
import time
import ctypes
import csv

from util import load_package_path
cache_path, _,_ = load_package_path()

import pyodbc
from tabulate import tabulate
from connect import ConnectorODBC
import sqlparse

# Global connection object
conn = None

print(os.getcwd())

class SoStartConn(sublime_plugin.WindowCommand):
    def run(self):
        """Initialize ODBC connection when command is triggered"""
        global conn
        
        # Check if environment variables are set
        if os.getenv("SQLUSERNAMEENCODED") and os.getenv("SQLPWENCODED"):
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
            sublime.error_message(
                "Environment variables SQLUSERNAMEENCODED and SQLPWENCODED are not set. "
                "Please set these variables before starting the connection."
            )

    def get_connect(self):
        """Establish connection to database"""
        try:
            global conn
            conn = ConnectorODBC(use_env_vars=True)  
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


class SoRunSqlCmd(sublime_plugin.WindowCommand):
    def run(self, limit, number_of_cache_query, timeout, output_in_panel, queries=None):
        def main_func(self, *args):
            limit, number_of_cache_query, queries = args
            print(queries)

            try:
                view = self.window.active_view()
                # currently only takes single cursor query selection
                print("conn is ", conn)
                cursor = view.sel()[0]
                a = cursor.begin()
                b = cursor.end()

                if a > b:
                    a, b = b, a
                if queries is None:
                    queries = view.substr(sublime.Region(a, b))
                queries = queries.split(";")

                if view.file_name() is not None:
                    panel_name = os.path.basename(view.file_name())
                else:
                    panel_name = view.name()
                if panel_name == "":
                    panel_name = "untitled"

                for query in queries:
                    if set(query) == {"\n"}:
                        continue
                    # query = query.replace(";", "")
                    parsed = sqlparse.parse(query)[0]

                    if limit:
                        has_limit = True
                    else:
                        has_limit = False

                    if " top " in query.lower() or " sample " in query.lower():
                        has_sample = True
                    else:
                        has_sample = False
                    if output_in_panel:
                        # create panel
                        panel = self.window.create_output_panel("result")
                    else:
                        num_groups = self.window.num_groups()
                        if num_groups <= 1:
                            self.window.run_command("new_file")
                            self.window.run_command("new_pane")
                            self.window.set_layout(
                                {
                                    "cols": [0.0, 1.0],
                                    "rows": [0.0, 0.55, 1.0],
                                    "cells": [[0, 0, 1, 1], [0, 1, 1, 2]],
                                }
                            )
                            self.window.focus_group(1)
                        else:
                            num_groups = self.window.num_groups()
                            if num_groups > 1:
                                self.window.focus_group(1)
                            self.window.run_command("new_file")

                        all_views_name = list(
                            map(lambda x: x.name(), self.window.views())
                        )
                        all_result = [
                            i.split("Query Result")[1].strip()
                            for i in all_views_name
                            if "Query Result" in i
                        ]
                        if len(all_result) == 0:
                            view_name = "Query Result 0"
                        else:
                            result_idx = []
                            for i in all_result:
                                try:
                                    idx = int(i)
                                    result_idx.append(idx)
                                except:
                                    pass
                            max_idx = max(result_idx) + 1
                            view_name = f"Query Result {max_idx}"

                        panel = self.window.active_view()
                        panel.set_name(view_name)
                        panel.set_scratch(True)
                    panel.set_read_only(False)
                    panel.settings().set("word_wrap", False)

                    # load cache query
                    cache_dict = load_cache_dict(cache_path)
                    result = cache_dict.get(query)
                    if result is None:
                        is_not_cache = True
                    else:
                        to_return = result
                        is_not_cache = False
                        panel.run_command("append", {"characters": f"{to_return}"})
                        panel.run_command(
                            "append",
                            {"characters": "\n\n\nReturn from Cache"},
                        )
                        panel.run_command(
                            "append",
                            {
                                "characters": f"\n{len(cache_dict)}/{number_of_cache_query}  (num of query in cache vs maxium cache)"
                            },
                        )

                    # only execute when there is no cache
                    if is_not_cache:
                        start = time.time()
                        try:
                            # Use ConnectorODBC's execute method
                            conn.execute(query)
                            dur = time.time() - start
                            print("query is ,", query)
                            has_exec_error = False
                        except Exception as e:
                            error = e
                            has_exec_error = True
                            print(error)
                            dur = time.time() - start

                        if not has_exec_error:
                            rowcount = conn.cursor.rowcount

                            try:
                                if has_sample or not has_limit:
                                    result = conn.cursor.fetchall()
                                else:
                                    result = conn.cursor.fetchmany(limit)
                                has_return_msg = True
                            except Exception as fetch_error:
                                print(f"Fetch error: {fetch_error}")
                                if parsed.get_type() != "UNKNOWN":
                                    if conn.cursor.rowcount == -1:
                                        to_return = f"Successfully run {parsed.get_type().lower()} statement in {round(dur,2)} seconds!"
                                    else:
                                        to_return = f"Successfully run {parsed.get_type().lower()} statement in {round(dur,2)} seconds!\n{conn.cursor.rowcount} rows impacted "
                                else:
                                    to_return = f"Successfully run statement in {round(dur,2)} seconds!"

                                has_return_msg = False
                        else:
                            has_return_msg = False

                        if not has_exec_error and has_return_msg:
                            cols = [row[0] for row in conn.cursor.description]
                            result2 = []
                            for i in result:
                                result2.append(
                                    tuple(
                                        j.replace("\n", " ")
                                        if isinstance(j, str)
                                        else j
                                        for j in i
                                    )
                                )

                            to_return = tabulate(
                                result2, cols, "psql", disable_numparse=True
                            )
                            # write to a cache file
                            new_cache = {query: to_return}
                            cache_dict = add_result_to_cache(
                                cache_dict, new_cache, number_of_cache_query
                            )
                            cache_dict_to_write = json.dumps(cache_dict)

                            with open(cache_path, "w") as f:
                                f.write(cache_dict_to_write)

                            panel.run_command("append", {"characters": f"{to_return};"})
                            panel.run_command(
                                "append",
                                {
                                    "characters": f"\n\n\nActual Query retrieve time {round(dur,2)}, total rows retrieved are {rowcount}"
                                },
                            )

                            if has_limit and not has_sample and len(result) == limit:
                                panel.run_command(
                                    "append",
                                    {
                                        "characters": f"\nATTENTION! RESULT OMITTED!\nOnly showed {limit} out of {rowcount} rows, change limit under `sa_run_sql_cmd` in keybind or explicitly pass sample number"
                                    },
                                )

                        elif not has_exec_error and not has_return_msg:
                            panel.run_command("append", {"characters": f"{to_return}"})
                        elif has_exec_error:
                            # to_return = str(error) + "\n\n" + "Query Runned:\n" + query
                            to_return = str(error)
                            panel.run_command("append", {"characters": f"{to_return}"})

                    if output_in_panel:
                        self.window.run_command(
                            "show_panel", {"panel": "output.result"}
                        )
                    else:
                        query_run = f";\n\nQuery Executed;\n{query};\n"
                        panel.run_command("append", {"characters": f"{query_run}"})
                        panel.run_command(
                            "append",
                            {"characters": f"\nQuery run from tab: `{panel_name}`"},
                        )

                    panel.set_read_only(True)

            finally:
                pass

        def print_status_msg(self, t1, timeout):
            duration = 0
            while t1.is_alive() and duration < timeout:
                time.sleep(1)
                sublime.status_message(f"Executing SQL query for {duration} seconds...")
                duration += 1
            if duration >= timeout:
                stop_thread(t1)
                # sleep to wait until thread_active show as all stopped
                panel = self.window.create_output_panel("timeout")
                panel.set_read_only(False)
                panel.settings().set("word_wrap", False)
                # why this wierd threading._active.items() mark finished thread as unfinished?
                # All threads: {list(threading._active.items())}
                panel.run_command(
                    "insert",
                    {
                        "characters": f"Execution timeout after {timeout} seconds, thread_number {t1.native_id}.\nCheck VPN or increase timeout in key binding args for run_sql_cmd"
                    },
                )
                panel.set_read_only(True)
                self.window.run_command("show_panel", {"panel": "output.timeout"})

        # Check if connection is available
        if conn is not None:
            print(queries)
            t1 = threading.Thread(
                target=main_func,
                args=[self, limit, number_of_cache_query, queries],
                name="sa_run_sql_cmd",
            )
            t2 = threading.Thread(
                target=print_status_msg,
                args=[self, t1, timeout],
                name=f"sa_timeout_query",
            )
            t1.start()
            t2.start()
        else:
            sublime.message_dialog(
                "Database connection not established. Please run 'Start Connection' command first."
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
        all_thread = threading._active
        to_interrupt = []
        for tid, thread in all_thread.items():
            if (
                thread.name
                in [
                    "sa_run_sql_cmd",
                    "sa_timeout_query",
                    "meta_init",
                    "meta_timeout",
                    "meta_add",
                    "sa_connect",
                ]
                and thread.is_alive()
            ):
                to_interrupt.append(thread)
        if len(to_interrupt) == 0:
            return
        for thread in to_interrupt:
            stop_thread(thread)

        all_names = " , ".join(
            [f"{thread.name} {thread.native_id}" for thread in to_interrupt]
        )
        panel = self.window.create_output_panel("interrupt")
        panel.set_read_only(False)
        panel.settings().set("word_wrap", False)
        panel.run_command(
            "insert",
            {
                "characters": f"Successfully interrupt {all_names}\nAll thread: {list(threading._active.items())}"
            },
        )
        panel.set_read_only(True)
        self.window.run_command("show_panel", {"panel": "output.interrupt"})


class SaAddDotInWordSep(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings("Preferences.sublime-settings")
        sep = settings.get("word_separators")

        if "." not in sep:
            sep = "." + sep
            settings.set("word_separators", sep)
            msg = "Add dot from word_separator"
        elif "." in sep:
            sep = sep.replace(".", "")
            settings.set("word_separators", sep)
            msg = "Remove dot from word_separator"

        sublime.save_settings("Preferences.sublime-settings")

        panel = self.window.create_output_panel("dot")
        panel.set_read_only(False)
        panel.settings().set("word_wrap", False)
        panel.run_command(
            "insert",
            {"characters": msg},
        )
        panel.set_read_only(True)
        self.window.run_command("show_panel", {"panel": "output.dot"})


class SaRestartConnection(sublime_plugin.TextCommand):
    def run(self, edit):
        conn1 = str(conn)
        self.conn1 = conn1

        conn.close()
        self.restart()

    def restart(self):
        global conn
        conn = ConnectorODBC(use_env_vars=True)
        conn2 = str(conn)
        sublime.message_dialog("Restarted connection!")
        print("Before:", self.conn1, "\n", "After:", conn2)


class TblToCsv(sublime_plugin.WindowCommand):
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


class DataDictionary(sublime_plugin.WindowCommand):
    def run(self):
        conn.execute(
            """
        select distinct "db","tbl","column" from team_caf.metastore
        """
        )

        result = conn.cursor.fetchall()

        db_lst = set()
        tbl_lst = set()
        col_lst = set()

        for row in result:
            db, tbl, col = row
            db_tbl = ".".join((db, tbl))
            db_tbl_col = ".".join((db, tbl, col))
            db_lst.add(db)
            tbl_lst.add(db_tbl)
            col_lst.add(db_tbl_col)


        self.col_lst = list(db_lst) + list(tbl_lst) + list(col_lst)
        self.window.show_quick_panel(self.col_lst, self.on_done, 0, 0)

    def on_done(self, index):
        if index == -1:
            return
        select = self.col_lst[index]

        if select.count(".") == 0:
            # db
            self.window.run_command(
                "sa_run_sql_cmd",
                args={
                    "limit": None,
                    "number_of_cache_query": 20,
                    "timeout": 360,
                    "output_in_panel": False,
                    "queries": f"""select 
                    a.db,
                    a.tbl,
                    a."column",
                    a.dtype,
                    a.definition,
                    a.num_of_null,
                    a.null_percent,
                    a.num_of_distinct,
                    a.distinct_val,
                    a.minval,
                    a.maxval,
                    a.insert_date,
                    a.contact 
                    from team_caf.metastore as a where "db" = '{db}' 
                    """,
                },
            )
        elif select.count(".") == 1:
            db, tbl = select.split(".")
            self.window.run_command(
                "sa_run_sql_cmd",
                args={
                    "limit": None,
                    "number_of_cache_query": 20,
                    "timeout": 360,
                    "output_in_panel": False,
                    "queries": f"""select
                    a.db,
                    a.tbl,
                    a."column",
                    a.dtype,
                    a.definition,
                    a.num_of_null,
                    a.null_percent,
                    a.num_of_distinct,
                    a.distinct_val,
                    a.minval,
                    a.maxval,
                    a.insert_date,
                    a.contact 
                    from team_caf.metastore as a where "db" = '{db}' and "tbl" = '{tbl}' """,
                },
            )
        else:
            db, tbl, col = select.split(".")
            self.window.run_command(
                "sa_run_sql_cmd",
                args={
                    "limit": None,
                    "number_of_cache_query": 20,
                    "timeout": 360,
                    "output_in_panel": False,
                    "queries": f"""select 
                    a.db,
                    a.tbl,
                    a."column",
                    a.dtype,
                    a.definition,
                    a.num_of_null,
                    a.null_percent,
                    a.num_of_distinct,
                    a.distinct_val,
                    a.minval,
                    a.maxval,
                    a.insert_date,
                    a.contact 
                    from team_caf.metastore as a where "db" = '{db}' and "tbl" = '{tbl}' and "column" = '{col}' """,
                },
            )
