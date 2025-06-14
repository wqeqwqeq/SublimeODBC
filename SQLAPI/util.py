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


def load_settings(settings_path="SQLOdbc.sublime-settings", get_cur_dbms_only=False, get_cur_selection_only=False, get_dbms_setting_only=False):
    """Load settings from the settings file
    
    Args:
        settings_path: Path to the settings file
        get_cur_dbms_only: If True, return only the current DBMS string
        get_cur_selection_only: If True, return only the current selection string
        get_dbms_setting_only: If True, return only the DBMS setting dict
    Returns:    
        dict or str: Full settings dict or current DBMS string if get_cur_dbms_only=True or current selection string if get_cur_selection_only=True
    """
    try:
        with open(settings_path, "r") as f:
            settings = json.loads(f.read())
        
        if get_cur_dbms_only:
            return settings.get('current_dbms', '')
        elif get_cur_selection_only:
            return settings.get('current_selection', '')
        elif get_dbms_setting_only:
            current_dbms = settings.get('current_dbms', '')
            settings = settings.get('DBMS_Setting', {}).get(current_dbms, {})
            return settings
        
        return settings
    except Exception as e:
        if get_cur_dbms_only:
            raise ValueError(f"Error loading current DBMS from {settings_path}: {str(e)}")
        elif get_cur_selection_only:
            raise ValueError(f"Error loading current selection from {settings_path}: {str(e)}")
        elif get_dbms_setting_only:
            raise ValueError(f"Error loading DBMS setting from {settings_path}: {str(e)}")
        else:
            raise ValueError(f"Error loading {settings_path}: {str(e)}")


def update_settings(key, value, settings_path="SQLOdbc.sublime-settings"):
    """Update a specific setting value and save to file
    
    Args:
        key: The setting key to update
        value: The new value for the setting
        settings_path: Path to the settings file
    """
    try:
        settings = load_settings(settings_path)
        settings[key] = value
        
        with open(settings_path, "w") as f:
            f.write(json.dumps(settings, indent=4))
    except Exception as e:
        raise ValueError(f"Error updating setting '{key}' in {settings_path}: {str(e)}")


def credential_set(show_msg=True):
    # Load settings to get current DBMS
    try:
        current_dbms = load_settings(get_cur_dbms_only=True).upper()
        if not current_dbms:
            if show_msg:
                sublime.message_dialog("current_dbms not found in settings")
            return False
    except Exception as e:
        if show_msg:
            sublime.message_dialog(f"Error loading settings: {str(e)}")
        return False
    
    # Load full settings to check if connection string needs credentials
    try:
        settings = load_settings()
        db_config = settings.get('DBMS_Setting', {}).get(current_dbms.lower())
        if not db_config:
            if show_msg:
                sublime.message_dialog(f"Database configuration for '{current_dbms}' not found in settings")
            return False
            
        connection_string = db_config.get("connection_string", "")
        if not connection_string:
            if show_msg:
                sublime.message_dialog(f"Connection string not found for '{current_dbms}'")
            return False
            
        # If connection string doesn't need credentials, return True
        if '{SQL_USERNAME_ENCODED}' not in connection_string and '{SQL_PW_ENCODED}' not in connection_string:
            print(f"{connection_string} doesn't need credentials")
            return True
            
    except Exception as e:
        if show_msg:
            sublime.message_dialog(f"Error loading settings: {str(e)}")
        return False
    
    # Only check environment variables if credentials are needed
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