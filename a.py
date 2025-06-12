import sublime
import os
import sys


package_path = sublime.packages_path()
sys_path = f"{package_path}\\SublimeODBC\\lib"
sys_path2 = f"{package_path}\\SublimeODBC"
sys_path3 = f"{package_path}\\SublimeODBC\\SQLAPI"


if sys_path not in sys.path:
    sys.path.append(sys_path)
    sys.path.append(sys_path2)
    sys.path.append(sys_path3)


settings = sublime.load_settings("Preferences.sublime-settings")
sep = settings.get("word_separators")

if "."  in sep:
    sep = sep.replace(".", "")
    settings.set("word_separators", sep)
    settings.set("auto_complete_commit_on_tab", True)
    sublime.save_settings("Preferences.sublime-settings")


