import sublime
import sublime_plugin
import os
from operator import itemgetter
from SQLAPI.util import load_settings

package_path = sublime.packages_path()
plugin_path = f"{package_path}\\SQLOdbc"


class ViewConfig(sublime_plugin.WindowCommand):
    def run(self, read_only=True, file=None):
        if file == 'keymap':
            self._open_keymap(read_only)
        elif file == 'setting':
            self._open_settings(read_only)
        elif file == 'schema':
            self._open_schema(read_only)
        elif file is None:
            self._show_current_settings()
        else:
            sublime.error_message("Invalid file type specified")

    def _open_keymap(self, read_only):
        if read_only:
            with open(f"{plugin_path}\\Default (Windows).sublime-keymap", "r") as f:
                file = f.read()
            self.window.new_file()
            panel = self.window.active_view()
            panel.set_name("Default (Windows).sublime-keymap (Read-Only)")
            self.window.run_command("insert", {"characters": file})
            panel.assign_syntax("Packages/JSON/JSON.sublime-syntax")
            panel.window().run_command("js_format")
            panel.set_read_only(True)
            panel.set_scratch(True)
        else:
            self.window.run_command(
                "open_file",
                args={
                    "file": "${packages}/SQLOdbc/Default (Windows).sublime-keymap"
                },
            )

    def _open_settings(self, read_only):
        if read_only:
            with open(f"{plugin_path}\\SQLOdbc.sublime-settings", "r") as f:
                file = f.read()
            self.window.new_file()
            panel = self.window.active_view()
            panel.set_name("SQLOdbc.sublime-settings (Read-Only)")
            self.window.run_command("insert", {"characters": file})
            panel.assign_syntax("Packages/JSON/JSON.sublime-syntax")
            panel.window().run_command("js_format")
            panel.set_read_only(True)
            panel.set_scratch(True)
        else:
            self.window.run_command(
                "open_file",
                args={
                    "file": "${packages}/SQLOdbc/SQLOdbc.sublime-settings"
                },
            )

    def _show_current_settings(self):
        current_selection = load_settings(get_cur_selection_only=True)
        current_dbms = load_settings(get_cur_dbms_only=True)
        message = f"Current Connection Group: {current_selection}\nCurrent DBMS: {current_dbms}"
        sublime.message_dialog(message)

    def _open_schema(self, read_only):
        # Get current selection and dbms using load_settings
        current_selection = load_settings(get_cur_selection_only=True)
        current_dbms = load_settings(get_cur_dbms_only=True)
        
        if not current_selection or not current_dbms:
            sublime.error_message("Current selection or DBMS not set in settings")
            return

        schema_path = f"{plugin_path}\\metastore\\{current_dbms}\\{current_selection}\\db-schema-tbl-col.json"
        
        if read_only:
            try:
                with open(schema_path, "r") as f:
                    file = f.read()
                self.window.new_file()
                panel = self.window.active_view()
                panel.set_name(f"Schema - {current_selection} ({current_dbms}) (Read-Only)")
                self.window.run_command("insert", {"characters": file})
                panel.assign_syntax("Packages/JSON/JSON.sublime-syntax")
                panel.window().run_command("js_format")
                panel.set_read_only(True)
                panel.set_scratch(True)
            except FileNotFoundError:
                sublime.error_message(f"Schema file not found for {current_selection} in {current_dbms}")
        else:
            self.window.run_command(
                "open_file",
                args={
                    "file": schema_path
                },
            )


class RenameView(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        self.view = view
        name = view.name()
        if name != "":
            prompt = name
        else:
            prompt = ""
        input_panel = self.window.show_input_panel(
            "Enter Tab Name: ",
            prompt,
            self.on_done,
            None,
            None,
        )

    def on_done(self, name):
        self.view.set_name(name)
        if self.view.is_scratch() and "Query Result" not in name:
            self.view.set_scratch(False)
            print("Currently not a Scratch File")


class ResizeWindowGroup(sublime_plugin.WindowCommand):
    def run(self):
        layout = self.window.layout()
        rows = layout["rows"]
        cols = layout["cols"]
        if len(rows) == 3:
            is_row = True
        else:
            if len(cols) == 3:
                is_row = False

        if is_row:
            size = rows[1]
        else:
            size = cols[1]

        if is_row:
            if size > 0.8:
                new_rows = {"rows": [0.0, 0.6, 1.0]}
            else:
                new_rows = {"rows": [0.0, 0.99, 1.0]}
            layout.update(new_rows)
        else:
            if size > 0.8:
                new_cols = {"cols": [0.0, 0.6, 1.0]}
            else:
                new_cols = {"cols": [0.0, 0.99, 1.0]}
            layout.update(new_cols)
        self.window.set_layout(layout)


class ViewZoom(sublime_plugin.WindowCommand):
    def run(self, zoomin):
        view = self.window.active_view()
        current_size = view.settings().get("font_size")
        if zoomin:
            size = current_size + 1
            view.settings().set("font_size", size)
        else:
            size = current_size - 1
            view.settings().set("font_size", size)

        print("Current view size", size)


class SortTabsInOrder(sublime_plugin.TextCommand):
    def run(self, edit):
        file_views = []
        win = self.view.window()
        curr_view = win.active_view()
        for vw in win.views():

            if vw.file_name() is not None:
                panel_name = os.path.basename(vw.file_name())
                panel_name = panel_name.lower()
            else:
                # only works for Query Result
                panel_name = vw.name()
                if "Query Result " in panel_name:
                    panel_name = panel_name.replace("Query Result ", "")
                    panel_name = int(panel_name)
                    group, _ = win.get_view_index(vw)
                    file_views.append((panel_name, vw, group))
            if panel_name == "":
                panel_name = "zzzzzzzzzzzzzz"

        file_views.sort(key=itemgetter(2, 0))
        print(file_views)
        for index, (_, vw, group) in enumerate(file_views):
            if not index or group > prev_group:
                moving_index = 0
                prev_group = group
            else:
                moving_index += 1
            win.set_view_index(vw, group, moving_index)
        win.focus_view(curr_view)




class UploadCsvToTable(sublime_plugin.WindowCommand):
    def run(self):
        sublime.open_dialog(self.print_path)

    def print_path(self, path):
        self.path = path
        input_panel = self.window.show_input_panel(
            "Enter Table Name: ",
            "",
            self.on_done,
            None,
            None,
        )

    def on_done(self, user_input):
        print(user_input,self.path)



# class SetAsScratch(sublime_plugin.WindowCommand):
#     def run(self):
#         view = self.window.active_view()
#         if view.is_scratch():
#             view.set_scratch(False)
#             print("Currently not a Scratch File")
#         else:
#             view.set_scratch(True)
#             print("Currently is a Scratch File")
