import tkinter as tk
from tkinter import ttk, messagebox
from abc import ABC, abstractmethod
import json
import uuid
import sqlite3
from typing import Dict, List, Optional
import hashlib # For password hashing
import secrets # For generating secure salts
from PIL import Image, ImageTk
# --- Banking System Core Classes ---
# These classes define the business logic for accounts, customers, and the bank itself.
# They are designed to be independent of the GUI framework.

# Abstract Account class defines the basic structure and common operations for all accounts.
class Account(ABC):
    def __init__(self, account_number: str, account_holder_id: str, initial_balance: float = 0.0):
        self._account_number = account_number
        self._account_holder_id = account_holder_id
        self._balance = max(0.0, initial_balance) # Ensure balance is not negative initially

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def account_holder_id(self) -> str:
        return self._account_holder_id

    @abstractmethod
    def deposit(self, amount: float) -> bool:
        # Abstract method for depositing funds, must be implemented by subclasses.
        pass

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        # Abstract method for withdrawing funds, must be implemented by subclasses.
        pass

    def display_details(self) -> str:
        # Returns a formatted string of account details for display.
        return f"Acc No: {self._account_number}, Balance: ${self._balance:.2f}"

    def to_dict(self) -> dict:
        # Converts the Account object to a dictionary for serialization (e.g., to JSON or database).
        return {
            "account_number": self._account_number,
            "account_holder_id": self._account_holder_id,
            "balance": self._balance,
            "type": "account" # Generic type for base class
        }

    @staticmethod
    def from_dict(data: dict):
        # Static method to reconstruct an Account (or its subclass) object from a dictionary.
        # This is crucial for loading data from persistence layer (e.g., SQLite).
        if data.get("type") == "savings": # Use .get() for safer access
            return SavingsAccount(data["account_number"], data["account_holder_id"], data["balance"], data["interest_rate"])
        elif data.get("type") == "checking":
            return CheckingAccount(data["account_number"], data["account_holder_id"], data["balance"], data["overdraft_limit"])
        return None

# SavingsAccount class inherits from Account and adds interest rate specific logic.
class SavingsAccount(Account):
    def __init__(self, account_number: str, account_holder_id: str, initial_balance: float = 0.0, interest_rate: float = 0.01):
        super().__init__(account_number, account_holder_id, initial_balance)
        self._interest_rate = max(0.0, interest_rate) # Ensure interest rate is non-negative
        self.type = "savings" # Explicitly set type for proper serialization and reconstruction

    @property
    def interest_rate(self) -> float:
        return self._interest_rate

    @interest_rate.setter
    def interest_rate(self, value: float):
        self._interest_rate = max(0.0, value)

    def deposit(self, amount: float) -> bool:
        # Deposits money into the savings account.
        if amount <= 0:
            return False
        self._balance += amount
        return True

    def withdraw(self, amount: float) -> bool:
        # Withdraws money from the savings account.
        # Savings accounts do not allow overdrafts.
        if amount <= 0 or self._balance < amount:
            return False
        self._balance -= amount
        return True

    def apply_interest(self) -> None:
        # Calculates and adds interest to the current balance.
        self._balance += self._balance * self._interest_rate

    def display_details(self) -> str:
        # Overrides base method to include interest rate.
        return f"{super().display_details()}, Interest Rate: {self._interest_rate*100:.2f}%"

    def to_dict(self) -> dict:
        # Extends base to_dict to include savings-specific attributes.
        data = super().to_dict()
        data.update({"interest_rate": self._interest_rate, "type": self.type})
        return data

# CheckingAccount class inherits from Account and adds overdraft limit logic.
class CheckingAccount(Account):
    def __init__(self, account_number: str, account_holder_id: str, initial_balance: float = 0.0, overdraft_limit: float = 0.0):
        super().__init__(account_number, account_holder_id, initial_balance)
        self._overdraft_limit = max(0.0, overdraft_limit) # Ensure overdraft limit is non-negative
        self.type = "checking" # Explicitly set type

    @property
    def overdraft_limit(self) -> float:
        return self._overdraft_limit

    @overdraft_limit.setter
    def overdraft_limit(self, value: float):
        self._overdraft_limit = max(0.0, value)

    def deposit(self, amount: float) -> bool:
        # Deposits money into the checking account.
        if amount <= 0:
            return False
        self._balance += amount
        return True

    def withdraw(self, amount: float) -> bool:
        # Withdraws money from the checking account, respecting the overdraft limit.
        if amount <= 0 or self._balance - amount < -self._overdraft_limit:
            return False
        self._balance -= amount
        return True

    def display_details(self) -> str:
        # Overrides base method to include overdraft limit.
        return f"{super().display_details()}, Overdraft Limit: ${self._overdraft_limit:.2f}"

    def to_dict(self) -> dict:
        # Extends base to_dict to include checking-specific attributes.
        data = super().to_dict()
        data.update({"overdraft_limit": self._overdraft_limit, "type": self.type})
        return data

# Customer class manages customer details and their associated account numbers.
class Customer:
    def __init__(self, customer_id: str, name: str, address: str):
        self._customer_id = customer_id
        self._name = name
        self._address = address
        self._account_numbers: List[str] = [] # Stores account numbers associated with this customer

    @property
    def customer_id(self) -> str:
        return self._customer_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str):
        self._address = value

    @property
    def account_numbers(self) -> List[str]:
        return self._account_numbers.copy() # Return a copy to prevent direct modification

    def add_account_number(self, account_number: str) -> None:
        if account_number not in self._account_numbers:
            self._account_numbers.append(account_number)

    def remove_account_number(self, account_number: str) -> None:
        if account_number in self._account_numbers:
            self._account_numbers.remove(account_number)

    def display_details(self) -> str:
        return f"Customer ID: {self._customer_id}, Name: {self._name}, Address: {self._address}, Accounts: {len(self._account_numbers)}"

    def to_dict(self) -> dict:
        # Converts the Customer object to a dictionary for serialization.
        return {
            "customer_id": self._customer_id,
            "name": self._name,
            "address": self._address,
            "account_numbers": self._account_numbers
        }

    @staticmethod
    def from_dict(data: dict):
        # Static method to reconstruct a Customer object from a dictionary.
        customer = Customer(data["customer_id"], data["name"], data["address"])
        customer._account_numbers = data.get("account_numbers", []) # Safely load account numbers
        return customer

# Bank class manages the collection of customers and accounts, and handles data persistence.
class Bank:
    def __init__(self, db_file: str = "bank.db"):
        self.db_file = db_file
        self._customers: Dict[str, Customer] = {}
        self._accounts: Dict[str, Account] = {}
        self._init_db() # Initialize the database schema for banking data
        self._init_user_db() # Initialize the database schema for user authentication
        self._load_data() # Load existing banking data into memory

    def _init_db(self) -> None:
        # Connects to the SQLite database and creates tables for customers and accounts if they don't exist.
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_number TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def _init_user_db(self) -> None:
        # Creates a separate table for user authentication (username and hashed password).
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: str = None) -> (str, str):
        # Hashes a password using SHA256 with a randomly generated salt.
        # Returns the hex-encoded hash and the salt.
        if salt is None:
            salt = secrets.token_hex(16) # Generate a new 16-byte random salt
        
        hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return hashed_password, salt

    def register_user(self, username: str, password: str) -> bool:
        # Registers a new user with a hashed password.
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False # User already exists

        hashed_password, salt = self._hash_password(password)
        try:
            cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                           (username, hashed_password, salt))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error registering user: {e}")
            return False
        finally:
            conn.close()

    def authenticate_user(self, username: str, password: str) -> bool:
        # Authenticates a user by verifying their password against the stored hash.
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_hash, stored_salt = result
            provided_hash, _ = self._hash_password(password, stored_salt)
            return provided_hash == stored_hash
        return False # User not found or incorrect password

    def _load_data(self) -> None:
        # Loads customer and account data from the SQLite database into in-memory dictionaries.
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Load customers
        cursor.execute("SELECT data FROM customers")
        customer_rows = cursor.fetchall()
        for row in customer_rows:
            try:
                data = json.loads(row[0])
                customer = Customer.from_dict(data)
                self._customers[customer.customer_id] = customer
            except json.JSONDecodeError as e:
                print(f"Error decoding customer data from DB: {e} - Data: {row[0]}")
            except Exception as e:
                print(f"Unexpected error loading customer from DB: {e} - Data: {row[0]}")

        # Load accounts
        cursor.execute("SELECT data FROM accounts")
        account_rows = cursor.fetchall()
        for row in account_rows:
            try:
                data = json.loads(row[0])
                account = Account.from_dict(data)
                if account:
                    self._accounts[account.account_number] = account
            except json.JSONDecodeError as e:
                print(f"Error decoding account data from DB: {e} - Data: {row[0]}")
            except Exception as e:
                print(f"Unexpected error loading account from DB: {e} - Data: {row[0]}")
        conn.close()

    def _save_data(self) -> None:
        # Saves the current state of customers and accounts from memory back to the database.
        # Uses a transaction for atomicity to ensure data consistency.
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        conn.execute("BEGIN TRANSACTION")
        try:
            # Clear existing data before inserting current data to ensure a full sync.
            cursor.execute("DELETE FROM customers")
            for customer in self._customers.values():
                cursor.execute("INSERT OR REPLACE INTO customers (customer_id, data) VALUES (?, ?)",
                               (customer.customer_id, json.dumps(customer.to_dict())))

            cursor.execute("DELETE FROM accounts")
            for account in self._accounts.values():
                cursor.execute("INSERT OR REPLACE INTO accounts (account_number, data) VALUES (?, ?)",
                               (account.account_number, json.dumps(account.to_dict())))
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback() # Rollback changes if any error occurs during save
            print(f"Database save error: {e}")
        finally:
            conn.close()

    def add_customer(self, customer: Customer) -> bool:
        if customer.customer_id in self._customers:
            return False
        self._customers[customer.customer_id] = customer
        self._save_data()
        return True

    def remove_customer(self, customer_id: str) -> bool:
        if customer_id not in self._customers:
            return False
        # Prevent removal if customer still has associated accounts.
        if self._customers[customer_id].account_numbers:
            return False
        del self._customers[customer_id]
        self._save_data()
        return True

    def create_account(self, customer_id: str, account_type: str, initial_balance: float = 0.0, **kwargs) -> Optional[Account]:
        if customer_id not in self._customers:
            return None
        account_number = str(uuid.uuid4()) # Generate a unique ID for the new account
        account = None
        if account_type.lower() == "savings":
            account = SavingsAccount(account_number, customer_id, initial_balance, kwargs.get("interest_rate", 0.01))
        elif account_type.lower() == "checking":
            account = CheckingAccount(account_number, customer_id, initial_balance, kwargs.get("overdraft_limit", 0.0))
        else:
            return None # Invalid account type
        
        self._accounts[account_number] = account
        self._customers[customer_id].add_account_number(account_number)
        self._save_data()
        return account

    def deposit(self, account_number: str, amount: float) -> bool:
        if account_number not in self._accounts:
            return False
        success = self._accounts[account_number].deposit(amount)
        if success:
            self._save_data()
        return success

    def withdraw(self, account_number: str, amount: float) -> bool:
        if account_number not in self._accounts:
            return False
        success = self._accounts[account_number].withdraw(amount)
        if success:
            self._save_data()
        return success

    def transfer_funds(self, from_acc_num: str, to_acc_num: str, amount: float) -> bool:
        if from_acc_num not in self._accounts or to_acc_num not in self._accounts:
            return False
        if from_acc_num == to_acc_num: # Prevent transfer to the same account
            return False

        # Attempt withdrawal first; if successful, then attempt deposit. Rollback if deposit fails.
        if self._accounts[from_acc_num].withdraw(amount):
            if self._accounts[to_acc_num].deposit(amount):
                self._save_data() # Save changes only if both operations succeed
                return True
            else:
                self._accounts[from_acc_num].deposit(amount)  # Rollback the withdrawal
        return False

    def get_customer_accounts(self, customer_id: str) -> List[Account]:
        if customer_id not in self._customers:
            return []
        # Filter out any account numbers that might no longer exist in _accounts (e.g., if manually deleted)
        return [self._accounts[acc_num] for acc_num in self._customers[customer_id].account_numbers if acc_num in self._accounts]

    def get_all_customers_details(self) -> List[Dict]:
        # Returns a list of dictionaries, each representing a customer's data.
        return [customer.to_dict() for customer in self._customers.values()]

    def get_all_accounts_details(self) -> List[Dict]:
        # Returns a list of dictionaries, each representing an account's data.
        return [account.to_dict() for account in self._accounts.values()]

    def apply_all_interest(self) -> None:
        # Iterates through all accounts and applies interest to SavingsAccounts.
        for account in self._accounts.values():
            if isinstance(account, SavingsAccount): # Check if the account is a SavingsAccount
                account.apply_interest()
        self._save_data() # Save all changes after applying interest to all relevant accounts


# --- Tkinter GUI Application ---
# This class sets up the graphical user interface using Tkinter.

class BankingApp(tk.Tk):
    def __init__(self, bank_system: Bank):
        super().__init__()
        self.bank = bank_system # Link to the core banking system logic
        self.title("Banking System Dashboard")
        self.geometry("900x700") # Set initial window size
        self.configure(bg="#F0F2F5") # Set a light gray background color for the main window

        # --- Style Configuration for Tkinter Widgets ---
        # Using ttk.Style for a modern look and consistent styling across widgets.
        self.style = ttk.Style(self)
        self.style.theme_use('clam') # 'clam' provides a flat, modern appearance.

        # Configure styles for various widgets
        self.style.configure('TFrame', background='#F0F2F5')
        self.style.configure('TLabel', background='#F0F2F5', font=('Helvetica Neue', 10))
        self.style.configure('TEntry', padding=5, font=('Helvetica Neue', 10))
        self.style.configure('TButton', font=('Helvetica Neue', 10, 'bold'), padding=6)
        
        # Mapping button states for interactive effects (e.g., hover color)
        self.style.map('TButton',
                       foreground=[('active', 'white')], # Text color on hover
                       background=[('active', '#4CAF50')]) # Background color on hover (Green)

        # Custom button styles for different actions
        self.style.configure('Dark.TButton', background='#2196F3', foreground='white') # Blue primary action
        self.style.map('Dark.TButton',
                       background=[('active', '#1976D2')],
                       foreground=[('active', 'white')])

        self.style.configure('Danger.TButton', background='#F44336', foreground='white') # Red for destructive actions
        self.style.map('Danger.TButton',
                       background=[('active', '#D32F2F')],
                       foreground=[('active', 'white')])

        self.style.configure('Info.TButton', background='#FFC107', foreground='white') # Amber for informational actions
        self.style.map('Info.TButton',
                       background=[('active', '#FFA000')],
                       foreground=[('active', 'white')])
        
        # --- Authentication Setup ---
        self.authenticated = False
        self.login_frame = ttk.Frame(self, padding="30 30 30 30", style='TFrame')
        self.login_frame.pack(expand=True, fill='both')
        self._create_login_signup_ui()

        # --- Main Banking Dashboard (hidden initially) ---
        self.notebook = ttk.Notebook(self) # Will be packed after successful authentication

        # Create individual frames (tabs) for each major section of the banking system.
        self.customer_frame = ttk.Frame(self.notebook, padding="20 20 20 20")
        self.account_frame = ttk.Frame(self.notebook, padding="20 20 20 20")
        self.transaction_frame = ttk.Frame(self.notebook, padding="20 20 20 20")
        self.view_frame = ttk.Frame(self.notebook, padding="20 20 20 20")
        self.banking_ops_frame = ttk.Frame(self.notebook, padding="20 20 20 20")

        # Add frames as tabs to the notebook
        self.notebook.add(self.customer_frame, text='Customer Management')
        self.notebook.add(self.account_frame, text='Account Creation')
        self.notebook.add(self.transaction_frame, text='Transactions')
        self.notebook.add(self.view_frame, text='View Data')
        self.notebook.add(self.banking_ops_frame, text='Bank Operations')

        # Populate each tab with its specific widgets and functionality.
        self._create_customer_tab()
        self._create_account_tab()
        self._create_transaction_tab()
        self._create_view_tab()
        self._create_banking_ops_tab()

        # --- Message Display Area (shared for both login and main app) ---
        self.message_label = ttk.Label(self, text="", wraplength=800, foreground="blue", font=('Helvetica Neue', 10, 'italic'))
        self.message_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    def _show_message(self, message: str, message_type: str = "info"):
        # Helper function to display messages in the message_label.
        color = "blue"
        if message_type == "success":
            color = "green"
        elif message_type == "error":
            color = "red"
        
        self.message_label.configure(text=message, foreground=color)
        # Automatically clear the message after 5 seconds.
        self.after(5000, lambda: self.message_label.configure(text="", foreground="blue"))

    def _create_login_signup_ui(self):
        # Create a visually appealing login/signup card
        login_card_frame = ttk.Frame(self.login_frame, padding="25 25 25 25", style='TFrame')
        login_card_frame.pack(expand=True)
        
        # Add a sleek border around the card
        login_card_frame.configure(relief='solid', borderwidth=2, style='TFrame')
        self.style.configure('TFrame', bordercolor='#D0D0D0', background='#FFFFFF') # Light gray border, white background for card

        # --- Logo at the top of the login/signup page ---
        try:
            # Load the image using Pillow. Adjust path if needed.
            self.logo_image = Image.open("ChatGPT Image Jun 18, 2025, 10_30_30 PM.png")
            self.logo_image = self.logo_image.resize((150, 150), Image.LANCZOS) # Resize for display
            self.logo_photo = ImageTk.PhotoImage(self.logo_image)
            self.logo_label = tk.Label(login_card_frame, image=self.logo_photo, bg='#FFFFFF') # Use bg of card
            self.logo_label.image = self.logo_photo # Keep a reference!
            self.logo_label.pack(pady=10)
        except FileNotFoundError:
            print("Logo image not found. Please ensure 'ChatGPT Image Jun 18, 2025, 10_30_30 PM.jpg' is in the same directory.")
            self.logo_label = ttk.Label(login_card_frame, text="[Logo Missing]", font=('Helvetica Neue', 10, 'italic'))
            self.logo_label.pack(pady=10)
        except Exception as e:
            print(f"Error loading logo image: {e}")
            self.logo_label = ttk.Label(login_card_frame, text="[Logo Error]", font=('Helvetica Neue', 10, 'italic'))
            self.logo_label.pack(pady=10)


        ttk.Label(login_card_frame, text="Welcome to Banking System", font=('Helvetica Neue', 16, 'bold')).pack(pady=10)
        ttk.Label(login_card_frame, text="Please Login or Sign Up", font=('Helvetica Neue', 12)).pack(pady=5)

        ttk.Label(login_card_frame, text="Username:").pack(pady=(15, 0))
        self.username_entry = ttk.Entry(login_card_frame, width=40, font=('Helvetica Neue', 11))
        self.username_entry.pack(pady=5)

        ttk.Label(login_card_frame, text="Password:").pack(pady=(10, 0))
        self.password_entry = ttk.Entry(login_card_frame, width=40, show="*", font=('Helvetica Neue', 11))
        self.password_entry.pack(pady=5)

        # Buttons for Login and Sign Up
        button_frame = ttk.Frame(login_card_frame, style='TFrame')
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Login", command=self._handle_login, style='Dark.TButton').grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="Sign Up", command=self._handle_signup, style='Dark.TButton').grid(row=0, column=1, padx=10)

    def _handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self._show_message("Please enter both username and password.", "error")
            return

        if self.bank.authenticate_user(username, password):
            self.authenticated = True
            self._show_message(f"Welcome, {username}! Login successful.", "success")
            self._show_main_dashboard()
        else:
            self._show_message("Login failed. Invalid username or password.", "error")

    def _handle_signup(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self._show_message("Please enter both username and password.", "error")
            return
        
        if len(password) < 6:
            self._show_message("Password must be at least 6 characters long.", "error")
            return

        if self.bank.register_user(username, password):
            self._show_message(f"User '{username}' registered successfully. You can now log in.", "success")
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
        else:
            self._show_message("Sign up failed. Username might already exist.", "error")

    def _show_main_dashboard(self):
        # Destroy the login frame and pack the main banking notebook.
        self.login_frame.destroy()
        
        # --- Add logo to the main dashboard as well ---
        main_header_frame = ttk.Frame(self, padding="10 10 10 10", style='TFrame')
        main_header_frame.pack(fill=tk.X, anchor=tk.N) # Pack at the top
        
        try:
            # Re-use the logo photo if available, or load again if needed (e.g. if the object was GC'd)
            # For simplicity, we re-load. In a large app, manage PhotoImage objects carefully.
            dashboard_logo_image = Image.open("ChatGPT Image Jun 18, 2025, 10_30_30 PM.jpg")
            dashboard_logo_image = dashboard_logo_image.resize((50, 50), Image.LANCZOS) # Smaller for dashboard
            self.dashboard_logo_photo = ImageTk.PhotoImage(dashboard_logo_image)
            dashboard_logo_label = tk.Label(main_header_frame, image=self.dashboard_logo_photo, bg='#F0F2F5')
            dashboard_logo_label.image = self.dashboard_logo_photo
            dashboard_logo_label.pack(side=tk.LEFT, padx=10)
        except Exception as e:
            print(f"Error loading dashboard logo: {e}")
            ttk.Label(main_header_frame, text="[Logo Missing]", font=('Helvetica Neue', 9, 'italic')).pack(side=tk.LEFT, padx=10)

        ttk.Label(main_header_frame, text="Banking System Dashboard", font=('Helvetica Neue', 18, 'bold')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.notebook.pack(expand=True, fill='both', padx=10, pady=(0, 10)) # Adjust pady as header is now present

    def _create_customer_tab(self):
        # Section for adding a new customer
        add_customer_frame = ttk.LabelFrame(self.customer_frame, text="Add New Customer", padding="15")
        add_customer_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(add_customer_frame, text="Customer ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.add_customer_id_entry = ttk.Entry(add_customer_frame, width=30)
        self.add_customer_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(add_customer_frame, text="Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.add_customer_name_entry = ttk.Entry(add_customer_frame, width=30)
        self.add_customer_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(add_customer_frame, text="Address:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.add_customer_address_entry = ttk.Entry(add_customer_frame, width=30)
        self.add_customer_address_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(add_customer_frame, text="Add Customer", command=self._add_customer, style='Dark.TButton').grid(row=3, column=0, columnspan=2, pady=10)

        # Section for removing an existing customer
        remove_customer_frame = ttk.LabelFrame(self.customer_frame, text="Remove Customer", padding="15")
        remove_customer_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(remove_customer_frame, text="Customer ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.remove_customer_id_entry = ttk.Entry(remove_customer_frame, width=30)
        self.remove_customer_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(remove_customer_frame, text="Remove Customer", command=self._remove_customer, style='Danger.TButton').grid(row=1, column=0, columnspan=2, pady=10)

    def _add_customer(self):
        # Event handler for adding a customer.
        customer_id = self.add_customer_id_entry.get().strip()
        name = self.add_customer_name_entry.get().strip()
        address = self.add_customer_address_entry.get().strip()

        if not customer_id or not name or not address:
            self._show_message("Please fill all customer fields.", "error")
            return

        customer = Customer(customer_id, name, address)
        if self.bank.add_customer(customer):
            self._show_message("Customer added successfully.", "success")
            # Clear input fields after successful operation
            self.add_customer_id_entry.delete(0, tk.END)
            self.add_customer_name_entry.delete(0, tk.END)
            self.add_customer_address_entry.delete(0, tk.END)
        else:
            self._show_message("Customer ID already exists.", "error")

    def _remove_customer(self):
        # Event handler for removing a customer.
        customer_id = self.remove_customer_id_entry.get().strip()
        if not customer_id:
            self._show_message("Please enter a Customer ID.", "error")
            return
        
        if self.bank.remove_customer(customer_id):
            self._show_message("Customer removed successfully.", "success")
            self.remove_customer_id_entry.delete(0, tk.END)
        else:
            self._show_message("Customer not found or has active accounts.", "error")

    def _create_account_tab(self):
        # Section for creating a new account.
        create_account_frame = ttk.LabelFrame(self.account_frame, text="Create New Account", padding="15")
        create_account_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(create_account_frame, text="Customer ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.create_account_customer_id_entry = ttk.Entry(create_account_frame, width=30)
        self.create_account_customer_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(create_account_frame, text="Account Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.account_type_var = tk.StringVar(self)
        self.account_type_dropdown = ttk.Combobox(create_account_frame, textvariable=self.account_type_var,
                                                  values=["savings", "checking"], state="readonly", width=28)
        self.account_type_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        # Bind an event to update dynamic fields when account type is selected.
        self.account_type_dropdown.bind("<<ComboboxSelected>>", self._update_account_fields)

        ttk.Label(create_account_frame, text="Initial Balance:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.create_account_balance_entry = ttk.Entry(create_account_frame, width=30)
        self.create_account_balance_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Frame to hold dynamically appearing fields (interest rate or overdraft limit)
        self.dynamic_account_fields_frame = ttk.Frame(create_account_frame)
        self.dynamic_account_fields_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self._update_account_fields() # Initial call to set up fields (e.g., if "savings" is default)

        ttk.Button(create_account_frame, text="Create Account", command=self._create_account, style='Dark.TButton').grid(row=4, column=0, columnspan=2, pady=10)

    def _update_account_fields(self, event=None):
        # Dynamically displays relevant fields based on the selected account type.
        for widget in self.dynamic_account_fields_frame.winfo_children():
            widget.destroy() # Clear existing dynamic fields

        account_type = self.account_type_var.get()
        if account_type == "savings":
            ttk.Label(self.dynamic_account_fields_frame, text="Interest Rate (e.g., 0.01):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.create_account_rate_entry = ttk.Entry(self.dynamic_account_fields_frame, width=30)
            self.create_account_rate_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.create_account_rate_entry.insert(0, "0.01") # Default value for convenience
        elif account_type == "checking":
            ttk.Label(self.dynamic_account_fields_frame, text="Overdraft Limit:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.create_account_overdraft_entry = ttk.Entry(self.dynamic_account_fields_frame, width=30)
            self.create_account_overdraft_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.create_account_overdraft_entry.insert(0, "0.00") # Default value

    def _create_account(self):
        # Event handler for creating an account.
        customer_id = self.create_account_customer_id_entry.get().strip()
        account_type = self.account_type_var.get().strip()
        
        try:
            initial_balance = float(self.create_account_balance_entry.get())
            if initial_balance < 0:
                raise ValueError("Initial balance cannot be negative.")
        except ValueError:
            self._show_message("Please enter a valid positive initial balance.", "error")
            return

        options = {}
        if account_type == "savings":
            try:
                interest_rate = float(self.create_account_rate_entry.get())
                if interest_rate < 0:
                    raise ValueError("Interest rate cannot be negative.")
                options['interest_rate'] = interest_rate
            except ValueError:
                self._show_message("Please enter a valid positive interest rate.", "error")
                return
        elif account_type == "checking":
            try:
                overdraft_limit = float(self.create_account_overdraft_entry.get())
                if overdraft_limit < 0:
                    raise ValueError("Overdraft limit cannot be negative.")
                options['overdraft_limit'] = overdraft_limit
            except ValueError:
                self._show_message("Please enter a valid positive overdraft limit.", "error")
                return
        else:
            self._show_message("Please select an account type (savings or checking).", "error")
            return

        account = self.bank.create_account(customer_id, account_type, initial_balance, **options)
        if account:
            self._show_message(f"Account created: {account.display_details()}", "success")
            # Clear input fields
            self.create_account_customer_id_entry.delete(0, tk.END)
            self.create_account_balance_entry.delete(0, tk.END)
            # Reset dynamic fields
            self._update_account_fields()
        else:
            self._show_message("Failed to create account (check customer ID or account type).", "error")

    def _create_transaction_tab(self):
        # Section for depositing funds.
        deposit_frame = ttk.LabelFrame(self.transaction_frame, text="Deposit Funds", padding="15")
        deposit_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(deposit_frame, text="Account Number:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.deposit_acc_entry = ttk.Entry(deposit_frame, width=30)
        self.deposit_acc_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(deposit_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.deposit_amount_entry = ttk.Entry(deposit_frame, width=30)
        self.deposit_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(deposit_frame, text="Deposit", command=self._deposit, style='Dark.TButton').grid(row=2, column=0, columnspan=2, pady=10)

        # Section for withdrawing funds.
        withdraw_frame = ttk.LabelFrame(self.transaction_frame, text="Withdraw Funds", padding="15")
        withdraw_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(withdraw_frame, text="Account Number:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.withdraw_acc_entry = ttk.Entry(withdraw_frame, width=30)
        self.withdraw_acc_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(withdraw_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.withdraw_amount_entry = ttk.Entry(withdraw_frame, width=30)
        self.withdraw_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(withdraw_frame, text="Withdraw", command=self._withdraw, style='Dark.TButton').grid(row=2, column=0, columnspan=2, pady=10)

        # Section for transferring funds between accounts.
        transfer_frame = ttk.LabelFrame(self.transaction_frame, text="Transfer Funds", padding="15")
        transfer_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(transfer_frame, text="From Account:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.transfer_from_acc_entry = ttk.Entry(transfer_frame, width=30)
        self.transfer_from_acc_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(transfer_frame, text="To Account:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.transfer_to_acc_entry = ttk.Entry(transfer_frame, width=30)
        self.transfer_to_acc_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(transfer_frame, text="Amount:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.transfer_amount_entry = ttk.Entry(transfer_frame, width=30)
        self.transfer_amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(transfer_frame, text="Transfer", command=self._transfer_funds, style='Dark.TButton').grid(row=3, column=0, columnspan=2, pady=10)

    def _deposit(self):
        # Event handler for deposit operation.
        account_number = self.deposit_acc_entry.get().strip()
        try:
            amount = float(self.deposit_amount_entry.get())
            if amount <= 0:
                raise ValueError("Deposit amount must be positive.")
        except ValueError:
            self._show_message("Please enter a valid positive amount.", "error")
            return

        if self.bank.deposit(account_number, amount):
            account = self.bank._accounts.get(account_number)
            self._show_message(f"Deposit successful. New balance: ${account.balance:.2f}" if account else "Deposit successful.", "success")
            self.deposit_acc_entry.delete(0, tk.END)
            self.deposit_amount_entry.delete(0, tk.END)
        else:
            self._show_message("Deposit failed. Account not found or invalid amount.", "error")

    def _withdraw(self):
        # Event handler for withdrawal operation.
        account_number = self.withdraw_acc_entry.get().strip()
        try:
            amount = float(self.withdraw_amount_entry.get())
            if amount <= 0:
                raise ValueError("Withdrawal amount must be positive.")
        except ValueError:
            self._show_message("Please enter a valid positive amount.", "error")
            return

        if self.bank.withdraw(account_number, amount):
            account = self.bank._accounts.get(account_number)
            self._show_message(f"Withdrawal successful. New balance: ${account.balance:.2f}" if account else "Withdrawal successful.", "success")
            self.withdraw_acc_entry.delete(0, tk.END)
            self.withdraw_amount_entry.delete(0, tk.END)
        else:
            self._show_message("Withdrawal failed. Account not found or insufficient funds/overdraft limit exceeded.", "error")

    def _transfer_funds(self):
        # Event handler for funds transfer operation.
        from_acc = self.transfer_from_acc_entry.get().strip()
        to_acc = self.transfer_to_acc_entry.get().strip()
        try:
            amount = float(self.transfer_amount_entry.get())
            if amount <= 0:
                raise ValueError("Transfer amount must be positive.")
        except ValueError:
            self._show_message("Please enter a valid positive amount.", "error")
            return

        if self.bank.transfer_funds(from_acc, to_acc, amount):
            from_acc_obj = self.bank._accounts.get(from_acc)
            to_acc_obj = self.bank._accounts.get(to_acc)
            self._show_message(f"Transfer successful. From: ${from_acc_obj.balance:.2f} To: ${to_acc_obj.balance:.2f}", "success")
            self.transfer_from_acc_entry.delete(0, tk.END)
            self.transfer_to_acc_entry.delete(0, tk.END)
            self.transfer_amount_entry.delete(0, tk.END)
        else:
            self._show_message("Transfer failed. Check account numbers, insufficient funds, or transferring to the same account.", "error")

    def _create_view_tab(self):
        # Section to view accounts for a specific customer.
        view_customer_accounts_frame = ttk.LabelFrame(self.view_frame, text="View Customer Accounts", padding="15")
        view_customer_accounts_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(view_customer_accounts_frame, text="Customer ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.view_customer_id_entry = ttk.Entry(view_customer_accounts_frame, width=30)
        self.view_customer_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(view_customer_accounts_frame, text="View Accounts", command=self._view_customer_accounts, style='Info.TButton').grid(row=1, column=0, columnspan=2, pady=10)

        # Text widget to display customer's account details.
        self.customer_accounts_text = tk.Text(view_customer_accounts_frame, height=10, width=80, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 9))
        self.customer_accounts_text.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        # Configure row/column weights to make the text widget resizable.
        view_customer_accounts_frame.grid_rowconfigure(2, weight=1)
        view_customer_accounts_frame.grid_columnconfigure(1, weight=1)

        # Section to display all registered customers.
        display_all_customers_frame = ttk.LabelFrame(self.view_frame, text="Display All Customers", padding="15")
        display_all_customers_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Button(display_all_customers_frame, text="Display All Customers", command=self._display_all_customers, style='Info.TButton').pack(pady=5)
        self.all_customers_text = tk.Text(display_all_customers_frame, height=10, width=80, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 9))
        self.all_customers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Make it expandable

        # Section to display all created accounts.
        display_all_accounts_frame = ttk.LabelFrame(self.view_frame, text="Display All Accounts", padding="15")
        display_all_accounts_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Button(display_all_accounts_frame, text="Display All Accounts", command=self._display_all_accounts, style='Info.TButton').pack(pady=5)
        self.all_accounts_text = tk.Text(display_all_accounts_frame, height=10, width=80, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 9))
        self.all_accounts_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Make it expandable

    def _view_customer_accounts(self):
        # Event handler to display a customer's accounts.
        customer_id = self.view_customer_id_entry.get().strip()
        self.customer_accounts_text.config(state=tk.NORMAL) # Enable editing for update
        self.customer_accounts_text.delete(1.0, tk.END) # Clear previous content

        if not customer_id:
            self._show_message("Please enter a Customer ID to view accounts.", "error")
            self.customer_accounts_text.insert(tk.END, "Please enter a Customer ID.")
            self.customer_accounts_text.config(state=tk.DISABLED)
            return

        accounts = self.bank.get_customer_accounts(customer_id)
        if accounts:
            self.customer_accounts_text.insert(tk.END, f"Accounts for Customer ID {customer_id}:\n\n")
            for account in accounts:
                self.customer_accounts_text.insert(tk.END, account.display_details() + "\n")
            self._show_message(f"Displayed accounts for customer {customer_id}.", "success")
        else:
            self.customer_accounts_text.insert(tk.END, f"No accounts found for customer ID {customer_id} or customer does not exist.")
            self._show_message("No accounts found or customer does not exist.", "error")
        self.customer_accounts_text.config(state=tk.DISABLED) # Disable editing after update

    def _display_all_customers(self):
        # Event handler to display all customers.
        self.all_customers_text.config(state=tk.NORMAL)
        self.all_customers_text.delete(1.0, tk.END)
        customers_data = self.bank.get_all_customers_details()
        if customers_data:
            self.all_customers_text.insert(tk.END, "All Customers:\n\n")
            for customer_dict in customers_data:
                # Reconstruct Customer object for using display_details method
                customer = Customer(customer_dict['customer_id'], customer_dict['name'], customer_dict['address'])
                customer._account_numbers = customer_dict['account_numbers'] # Needed for account count in display_details
                self.all_customers_text.insert(tk.END, customer.display_details() + "\n")
            self._show_message("Displayed all customers.", "success")
        else:
            self.all_customers_text.insert(tk.END, "No customers to display.")
            self._show_message("No customers to display.", "error")
        self.all_customers_text.config(state=tk.DISABLED)

    def _display_all_accounts(self):
        # Event handler to display all accounts.
        self.all_accounts_text.config(state=tk.NORMAL)
        self.all_accounts_text.delete(1.0, tk.END)
        accounts_data = self.bank.get_all_accounts_details()
        if accounts_data:
            self.all_accounts_text.insert(tk.END, "All Accounts:\n\n")
            for account_dict in accounts_data:
                # Reconstruct Account object to use its display_details method.
                account = Account.from_dict(account_dict)
                if account: # Ensure account reconstruction was successful
                    self.all_accounts_text.insert(tk.END, account.display_details() + "\n")
            self._show_message("Displayed all accounts.", "success")
        else:
            self.all_accounts_text.insert(tk.END, "No accounts to display.")
            self._show_message("No accounts to display.", "error")
        self.all_accounts_text.config(state=tk.DISABLED)

    def _create_banking_ops_tab(self):
        # Section for global bank operations, like applying interest.
        banking_ops_frame = ttk.LabelFrame(self.banking_ops_frame, text="Global Bank Operations", padding="15")
        banking_ops_frame.pack(fill=tk.X, pady=10, padx=5)

        ttk.Button(banking_ops_frame, text="Apply Interest to All Savings Accounts", command=self._apply_interest, style='Dark.TButton').pack(pady=10)

    def _apply_interest(self):
        # Event handler for applying interest to all savings accounts.
        self.bank.apply_all_interest()
        self._show_message("Interest applied to all savings accounts. Balances updated.", "success")
        # You might want to refresh the display of all accounts here if the user is on the "Display All Accounts" tab.


if __name__ == "__main__":
    # This block ensures the application runs when the script is executed directly.
    bank_system = Bank() # Initialize the Bank system; this will load data from or create 'bank.db'.
    app = BankingApp(bank_system) # Create an instance of the Tkinter application.
    app.mainloop() # Start the Tkinter event loop, which keeps the GUI running.
