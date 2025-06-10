import sublime
import os
import sys


package_path = sublime.packages_path()
cache_path = os.path.join(
    package_path, "SublimeODBC", "metastore", "cache_query.json"
)
sys_path = f"{package_path}\\SublimeODBC\\lib"
sys_path2 = f"{package_path}\\SublimeODBC"


if sys_path not in sys.path:
    sys.path.append(sys_path)
    sys.path.append(sys_path2)







