import sublime_plugin
import sublime
import os
import json
from SQLAPI.util import load_package_path  
import re 



cache_path, lib_path, plugin_path, js_path = load_package_path()

# do we need to lower the completion column?




class EventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        syntax = view.settings().get("syntax")
        # only trigger when the syntax is snowflake

        if syntax == "Packages/SQL/SQL.sublime-syntax":
            content = self.get_single_cursor_content(view)
            prev_words = self.get_multi_cursor_pre_word(view)
            alias_dict = self.find_alias(content)
            
            
            self.completions = []
            print("prev_words: ", prev_words)
            print("content: ", content)
            print("alias_dict: ", alias_dict)

            if len(prev_words) == 0:
                self.fill_db()

            for w in prev_words:
                ct = w.count(".")
                # db level
                if ct == 0:
                    self.fill_db()
                elif ct == 1:
                    print("fill schema")
                    self.fill_schema(w)
                    self.fill_alias(alias_dict)
                elif ct == 2:
                    self.fill_table(w)
                elif ct == 3:
                    self.fill_column(w)

            return (self.completions, sublime.INHIBIT_WORD_COMPLETIONS)

    # TODO: 就近分配原则
    def find_alias(self, content):
        alias_dict = {}
        pattern1 = r"from\s+(\S+)\s+as\s+(\w+)"
        matches1 = re.findall(pattern1, content, re.IGNORECASE)

        for match in matches1:
            tbl, alias = match
            alias_dict[alias] = tbl

        pattern2 = r"join\s+(\S+)\s+as\s+(\w+)"
        matches2 = re.findall(pattern2, content, re.IGNORECASE)

        for match in matches2:
            tbl, alias = match
            alias_dict[alias] = tbl
        return alias_dict

    def fill_alias(self, alias_dict):
        if alias_dict:
            db_schema_tbl_col = self.load_js("db-schema-tbl-col")

            for alias, tbl in alias_dict.items():
                if tbl.count(".") != 2:
                    continue
                db, schema, tbl = tbl.split(".")
                if (
                    db_schema_tbl_col.get(db)
                    and schema in db_schema_tbl_col.get(db)
                    and tbl in db_schema_tbl_col.get(db).get(schema)
                ):
                    cols = db_schema_tbl_col[db][schema][tbl]
                    for col, dtype in cols.items():
                        dtype = map2.get(dtype) if map2.get(dtype) else dtype
                        txt_show = alias + "." + col + "\t" + dtype
                        txt_fill = alias + "." + col
                        self.completions.append((txt_show, txt_fill))

    def get_multi_cursor_pre_word(self, view):
        input_cursor_word = []
        for cursor in view.sel():
            if cursor.begin() > 0:
                word_region = view.word(cursor.begin() - 1)
                word = view.substr(word_region)
                input_cursor_word.append(word)

        return input_cursor_word

    def fill_db(self):
        db_schema = self.load_js("db-schema")
        for db in db_schema:
            txt_show = db + "\tdatabase"
            txt_fill = db
            self.completions.append((txt_show, txt_fill))

    def fill_schema(self, w):
        db_schema = self.load_js("db-schema")
        db, schema = w.split(".")
        schemas = db_schema.get(db)
        if schemas:
            for s in schemas:
                txt_show = s + "\tschema"
                txt_fill = s
                self.completions.append((txt_show, txt_fill))

    # temporarily try query method
    def fill_table(self, w):
        db_schema_tbl = self.load_js("db-schema-tbl")
        db, schema, _ = w.split(".")
        if db_schema_tbl.get(db) and schema in db_schema_tbl.get(db):
            tbls = db_schema_tbl[db][schema]
            for r in tbls:
                txt_show = r + "\ttable"
                txt_fill = r
                self.completions.append((txt_show, txt_fill))

    def fill_column(self, w):
        db_schema_tbl_col = self.load_js("db-schema-tbl-col")
        db, schema, tbl, _ = w.split(".")
        if (
            db_schema_tbl_col.get(db)
            and schema in db_schema_tbl_col.get(db)
            and tbl in db_schema_tbl_col.get(db).get(schema)
        ):
            cols = db_schema_tbl_col[db][schema][tbl]
            expand_cols = ",".join([f"a.{c}" for c in cols])

            special_txt_show1 = db + "." + schema + "." + tbl + "." + "*" + "\t" + "all"
            special_txt_show2 = (
                db + "." + schema + "." + tbl + "." + "-" + "\t" + "expand"
            )
            special_txt_show3 = (
                db + "." + schema + "." + tbl + "." + "Count(*)" + "\t" + "cnt"
            )

            special_txt_fill1 = f"SELECT a.*$0 FROM {db}.{schema}.{tbl} as a;"
            special_txt_fill2 = f"SELECT $0{expand_cols} FROM {db}.{schema}.{tbl} as a;"
            special_txt_fill3 = f"SELECT $0COUNT(*) FROM {db}.{schema}.{tbl} as a;"

            # TO DO: fuzzy fill all

            self.completions = [
                (special_txt_show1, special_txt_fill1),
                (special_txt_show2, special_txt_fill2),
                (special_txt_show3, special_txt_fill3),
            ]

            for col, dtype in cols.items():
                txt_show = db + "." + schema + "." + tbl + "." + col + "\t" + dtype
                txt_fill = f"SELECT a.{col}$0 FROM {db}.{schema}.{tbl} as a;"
                self.completions.append((txt_show, txt_fill))

    # mainly for alias mapping
    def get_single_cursor_content(self, view):
        cursors = view.sel()
        semicolon = list(map(lambda x: x.begin(), view.find_all(";")))

        if len(semicolon) == 0:
            start, end = 0, view.size()
        elif len(semicolon) == 1 and len(cursors) == 1:
            cursor = cursors[0]
            if cursor.a <= semicolon[0]:
                start, end = 0, semicolon[0]
            else:
                start, end = semicolon[0], view.size()
        elif len(semicolon) > 1 and len(cursors) == 1:
            cursor = cursors[0]
            lst = list(sorted(semicolon + [0, cursor.a, view.size()]))
            idx = lst.index(cursor.a)
            pre_idx = max(0, idx - 1)
            post_idx = min(len(lst) - 1, idx + 1)
            start, end = lst[pre_idx], lst[post_idx]
        else:
            return
        content = view.substr(sublime.Region(start, end))
        content = content.replace(";", "")
        return content

    def load_js(self, file):
         
        with open("SQL.settings", "r") as f:
            custom_completions = json.loads(f.read())
            current_selection = custom_completions.get("current_selection")
            current_dbms = custom_completions.get("current_dbms")

        auto_completion_path = os.path.join(js_path, current_dbms, current_selection, f"{file}.json")

        with open(auto_completion_path, "r") as f:
            schema = json.loads(f.read())
        return schema
