import os
import base64
import json
import sublime
import sys
import re

# Regular expression for comments
comment_re = re.compile(
    '(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
    re.DOTALL | re.MULTILINE
)


def parse_json(filename):
    """Parse a JSON file
    First remove comments and then use the json module package
    Comments look like :
        // ...
    or
        /*
        ...
        */
    """
    with open(filename, mode='r', encoding='utf-8') as f:
        content = ''.join(f.readlines())

        # Looking for comments
        match = comment_re.search(content)
        while match:
            # single line comment
            content = content[:match.start()] + content[match.end():]
            match = comment_re.search(content)

        # remove trailing commas
        content = re.sub(r',([ \t\r\n]+)}', r'\1}', content)
        content = re.sub(r',([ \t\r\n]+)\]', r'\1]', content)

        # Return json file
        return json.loads(content, encoding='utf-8')


def save_json(content, filename):
    """Save content to JSON file with formatting"""
    with open(filename, mode='w', encoding='utf-8') as outfile:
        json.dump(content, outfile,
                  sort_keys=True, indent=2, separators=(',', ': '))


def merge_dict(source, destination):
    """
    Recursively merge source dict into destination dict
    
    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge_dict(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge_dict(value, node)
        else:
            destination[key] = value

    return destination


class SettingsManager:
    """Manages user and default settings with automatic merging"""
    
    def __init__(self, user_filename, default_filename=None):
        self.user_filename = user_filename
        self.default_filename = default_filename
        self.items = {}
        self._load_all()

    def _load_all(self):
        """Load and merge user and default settings"""
        # Load user settings if they exist
        if os.path.exists(self.user_filename):
            try:
                self.items = parse_json(self.user_filename)
            except Exception:
                self.items = {}
        else:
            self.items = {}

        # Merge with defaults if default file exists
        return merge_dict(self.items, self._get_defaults())

    def _get_defaults(self):
        """Get default settings from default file"""
        if self.default_filename and os.path.isfile(self.default_filename):
            try:
                return parse_json(self.default_filename)
            except Exception:
                return {}
        return {}

    def get_all(self):
        """Get all settings (merged user + default)"""
        return self._load_all()

    def get(self, key, default=None):
        """Get a specific setting value"""
        settings = self.get_all()
        return settings.get(key, default)

    def update(self, key, value):
        """Update a setting and save to user file"""
        self.items[key] = value
        self._save()

    def _save(self):
        """Save current items to user settings file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.user_filename), exist_ok=True)
        save_json(self.items, self.user_filename)


def load_package_path():
    package_path = sublime.packages_path()
    package_name = "SQLOdbc"

    cache_path = os.path.join(
        package_path, package_name, "metastore", "cache_query.json"
    )
    lib_path = f"{package_path}\\{package_name}\\lib"
    project_path = f"{package_path}\\{package_name}"
    metastore_path = f"{package_path}\\{package_name}\\metastore"
    user_path = os.path.join(sublime.packages_path(), 'User')

    if lib_path not in sys.path:
        sys.path.append(lib_path)
        sys.path.append(project_path)
    os.chdir(project_path)
    return cache_path, lib_path, project_path, metastore_path, user_path


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
    
    This function now handles two setting files - a default and a user setting file.
    If user settings exist, it merges them with default settings.
    
    Args:
        settings_path: Path to the settings file (user settings)
        get_cur_dbms_only: If True, return only the current DBMS string
        get_cur_selection_only: If True, return only the current selection string
        get_dbms_setting_only: If True, return only the DBMS setting dict
    Returns:    
        dict or str: Full settings dict or current DBMS string if get_cur_dbms_only=True or current selection string if get_cur_selection_only=True
    """
    try:
        # Define paths for user and default settings
        cache_path, lib_path, project_path, metastore_path, user_path = load_package_path()    
        
        
        SQLTOOLS_SETTINGS_FILE = settings_path
        
        SETTINGS_FILENAME = os.path.join(user_path, SQLTOOLS_SETTINGS_FILE)
        SETTINGS_FILENAME_DEFAULT = os.path.join(project_path, SQLTOOLS_SETTINGS_FILE)
        
        # Create SettingsManager instance that handles merging automatically
        settings_manager = SettingsManager(SETTINGS_FILENAME, SETTINGS_FILENAME_DEFAULT)
        
        # Get all settings (this returns merged settings from user + default)
        settings = settings_manager.get_all()
        
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
        # Define paths for user and default settings
        cache_path, lib_path, project_path, metastore_path, user_path = load_package_path()
        
        SQLTOOLS_SETTINGS_FILE = settings_path
        
        SETTINGS_FILENAME = os.path.join(user_path, SQLTOOLS_SETTINGS_FILE)
        SETTINGS_FILENAME_DEFAULT = os.path.join(project_path, f"default_{SQLTOOLS_SETTINGS_FILE}")
        
        # Create SettingsManager instance that handles merging automatically
        settings_manager = SettingsManager(SETTINGS_FILENAME, SETTINGS_FILENAME_DEFAULT)
        
        # Update the setting
        settings_manager.update(key, value)
        
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