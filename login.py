import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import sys
from util import crypt, load_config


class LoginGUI:
    def __init__(self, root, config_path="config.json"):
        self.root = root
        
        # Load config to determine database type
        self.db_config = load_config(config_path, strict=False)
        db_type = self.db_config.get('db_type', 'sqlserver')
        
        # Set title and labels based on database type
        db_titles = {
            'sqlserver': 'SQL Server Login',
            'mysql': 'MySQL Login', 
            'postgresql': 'PostgreSQL Login'
        }
        
        self.root.title(db_titles.get(db_type, 'Database Login'))
        self.root.geometry("400x220")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text=db_titles.get(db_type, 'Database Login'), font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=25)
        self.username_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=(0, 20))
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(main_frame, textvariable=self.password_var, show="*", width=25)
        self.password_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        # Login button
        self.login_button = ttk.Button(buttons_frame, text="Login", command=self.login)
        self.login_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Cancel button
        self.cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda event: self.login())
        
        # Focus on username entry
        self.username_entry.focus()
    

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def login(self):
        """Handle login button click"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            self.status_label.config(text="Please enter both username and password")
            return
        
        try:
            # Encode credentials using the crypt function from connect.py
            encoded_username = crypt(username, encode=True)
            encoded_password = crypt(password, encode=True)
            
            # Set environment variables permanently (Windows)
            success = self.set_environment_variables(encoded_username, encoded_password)
            
            if success:
                db_type = self.db_config.get('db_type', 'sqlserver')
                db_names = {
                    'sqlserver': 'SQL Server',
                    'mysql': 'MySQL',
                    'postgresql': 'PostgreSQL'
                }
                db_name = db_names.get(db_type, 'Database')
                
                messagebox.showinfo("Success", 
                    f"{db_name} login credentials have been saved successfully!\n"
                    "Environment variables SQLUSERNAMEENCODED and SQLPWENCODED have been set.\n"
                    "Please restart your applications to use the new credentials.")
                self.root.destroy()
            else:
                self.status_label.config(text="Failed to set environment variables")
                
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
    
    def set_environment_variables(self, encoded_username, encoded_password):
        """Set environment variables permanently on Windows"""
        try:
            if sys.platform == "win32":
                # Set user environment variables permanently on Windows
                subprocess.run([
                    "setx", "SQLUSERNAMEENCODED", encoded_username
                ], check=True, capture_output=True)
                
                subprocess.run([
                    "setx", "SQLPWENCODED", encoded_password
                ], check=True, capture_output=True)
                
                # Also set for current session
                os.environ["SQLUSERNAMEENCODED"] = encoded_username
                os.environ["SQLPWENCODED"] = encoded_password
                
                return True
            else:
                # For non-Windows systems, just set for current session
                # Note: This won't persist across sessions
                os.environ["SQLUSERNAMEENCODED"] = encoded_username
                os.environ["SQLPWENCODED"] = encoded_password
                messagebox.showwarning("Warning", 
                    "Environment variables set for current session only.\n"
                    "On non-Windows systems, you may need to manually add these to your shell profile.")
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"Error setting environment variables: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    
    def cancel(self):
        """Handle cancel button click"""
        self.root.destroy()


def DBMS_login():
    """Main function to run the login GUI"""
    root = tk.Tk()
    app = LoginGUI(root)
    root.mainloop()


if __name__ == "__main__":
    DBMS_login() 