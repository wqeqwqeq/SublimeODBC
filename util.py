import os
import base64
import json
import sublime
import sys



def load_package_path():
    package_path = sublime.packages_path()
    package_name = "SublimeODBC"

    cache_path = os.path.join(
        package_path, package_name, "metastore", "cache_query.json"
    )
    lib_path = f"{package_path}\\{package_name}\\lib"
    project_path = f"{package_path}\\{package_name}"


    if lib_path not in sys.path:
        sys.path.append(lib_path)
        sys.path.append(project_path)
    os.chdir(project_path)
    return cache_path, lib_path, project_path


def crypt(string, encoding="ascii", encode=True):
    """Encode or decode a string using base64"""
    string_encode = string.encode(encoding)
    if encode:
        base64_bytes = base64.b64encode(string_encode)
        print("Encoding...")
    else:
        base64_bytes = base64.b64decode(string_encode)
    return base64_bytes.decode(encoding)


def get_uid_pw():
    """Get encoded username and password from environment variables and decode them"""
    user = os.getenv("SQLUSERNAMEENCODED")
    assert user is not None, "SQL Server uid and pw not set, run setup_local in cmd"
    pw = os.getenv("SQLPWENCODED")
    return crypt(user, encode=False), crypt(pw, encode=False)


def load_config(config_path="config.json", strict=True):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        if strict:
            raise FileNotFoundError(f"Config file '{config_path}' not found")
        else:
            return {'db_type': 'sqlserver'}
    except json.JSONDecodeError:
        if strict:
            raise ValueError(f"Invalid JSON in config file '{config_path}'")
        else:
            return {'db_type': 'sqlserver'} 