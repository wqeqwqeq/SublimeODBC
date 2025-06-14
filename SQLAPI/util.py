import os
import base64
import json
import sublime
import sys



def load_package_path():
    package_path = sublime.packages_path()
    package_name = "SQLOdbc"

    cache_path = os.path.join(
        package_path, package_name, "metastore", "cache_query.json"
    )
    lib_path = f"{package_path}\\{package_name}\\lib"
    project_path = f"{package_path}\\{package_name}"
    metastore_path = f"{package_path}\\{package_name}\\metastore"

    if lib_path not in sys.path:
        sys.path.append(lib_path)
        sys.path.append(project_path)
    os.chdir(project_path)
    return cache_path, lib_path, project_path, metastore_path


def crypt(string, encoding="ascii", encode=True):
    """Encode or decode a string using base64"""
    string_encode = string.encode(encoding)
    if encode:
        base64_bytes = base64.b64encode(string_encode)
        print("Encoding...")
    else:
        base64_bytes = base64.b64decode(string_encode)
    return base64_bytes.decode(encoding)


def get_uid_pw(env_user_var, env_pw_var):
    """Get encoded username and password from environment variables and decode them"""
    user = os.getenv(env_user_var)
    assert user is not None, f"{env_user_var} not set, run setup_local in cmd"
    pw = os.getenv(env_pw_var)
    assert pw is not None, f"{env_pw_var} not set, run setup_local in cmd"
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

def load_settings(settings_path="SQL.settings"):
    try:
        with open(settings_path, "r") as f:
            settings = json.loads(f.read())
        return settings
    except Exception as e:
        raise ValueError(f"Error loading {settings_path}: {str(e)}")


def credential_set(show_msg=True):
    # Load SQL.settings
    try:
        settings = load_settings()
        current_dbms = settings.get("current_dbms", "").upper()
    except Exception as e:
        if show_msg:
            sublime.message_dialog(f"Error loading SQL.settings: {str(e)}")
        return False
    
    # Construct environment variable names based on current DBMS
    env_user_var = f"{current_dbms}USERNAMEENCODED"
    env_pw_var = f"{current_dbms}PWENCODED"
    
    if (
        os.getenv(env_user_var) is not None
        and os.getenv(env_pw_var) is not None
    ):
        if show_msg:
            sublime.message_dialog(f"{current_dbms} username and password has been set up!")
        return True
    else:
        if show_msg:
            sublime.message_dialog(f"{current_dbms} username or password not set up\nUse ctrl+e,ctrl+p to setup")
        return False 