import tkinter as tk
from tkinter import IntVar, messagebox, ttk
import socket
import threading
import sqlite3
import re
import uuid  # To generate unique transaction IDs

# Server configuration
HOST = '127.0.0.1'
PORT = 5000
BUFSIZE = 2048
INVENTORY_FILE = "inventory.txt"
TRANSACTION_FILE = "transactions.txt"

# Global variables
inventory = {}
cart = {}
user_activity = {}

def manage_client(conn):
    # Receive the client ID from the client
    client_id = conn.recv(BUFSIZE).decode('utf-8')
    print(f"Client {client_id} connected")

    initial_message = f"Client {client_id} connected to Vending Machine System."
    conn.sendall(initial_message.encode('utf-8'))

    print(f"Is socket closed? {conn._closed}")


def handle_command(socket_conn, command):
    """Handle communication with a connected client."""
    try:
        socket_conn.sendall(command.encode('utf-8'))
    except Exception as e:
        print(f"Error with command: {e}")


def start_server():
    """Start the server to handle multiple clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            socket_conn, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")

            manage_client(socket_conn)

            command = ''

            # Handle the client in a new thread
            client_thread = threading.Thread(target=handle_command, args=(socket_conn, command))
            client_thread.start()

class Product:
    def load_inventory(self):
        """Load inventory from file into a dictionary."""
        global inventory #calls global variable inventory
        inventory = {} #declares inventory as a dictionary
        try: #opens iteration
            with open(INVENTORY_FILE, "r") as file: #reads from variable INVENTORY_FILE
                lines = file.readlines() #stores each line in the file to lines
                if not lines: #compares
                    print("Warning: Inventory file is empty. Starting with an empty inventory.")
                for line in lines:
                    parts = line.split(", ")
                    item = {}
                    for part in parts:
                        key, value = part.split(": ")
                        key = key.strip()
                        value = value.strip()
                        if key in ["ID", "Quantity"]:
                            value = int(value)
                        elif key == "Price":
                            value = float(value)
                        item[key] = value
                    inventory[item["ID"]] = item
        except FileNotFoundError:
            print(f"Error: {INVENTORY_FILE} not found. Starting with empty inventory.")


    def save_inventory(self):
        """Save updated inventory back to file."""
        with open(INVENTORY_FILE, "w") as file:
            for item in inventory.values():
                file.write(
                    f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']}, Quantity: {item['Quantity']}\n"
                )


    # Modify save_transaction to save transactions in the database
    def save_transaction(self, cart, total_cost, db_conn, cursor):
        # Generate a unique transaction ID
        """Save completed transactions ensuring unique transaction IDs."""
        # Step 1: Load existing transaction IDs from the transactions file
        existing_ids = set()
        try:
            with open(TRANSACTION_FILE, "r") as file:
                lines = file.readlines()
                for line in lines:
                    if line.startswith("Transaction ID:"):
                        # Extract the ID and add it to the set
                        transaction_id = int(line.split(":")[1].strip())
                        existing_ids.add(transaction_id)
        except FileNotFoundError:
            print(f"Note: {TRANSACTION_FILE} not found. It will be created.")

        # Step 2: Generate a unique transaction ID
        while True:
            transaction_id = str(uuid.uuid4())
            if transaction_id not in existing_ids:
                break
        # Also save to the transactions.txt file for logging
        with open(TRANSACTION_FILE, "a") as file:
            file.write("\nOrder Receipt:\n")
            for item in cart.values():
                file.write(
                    f"ID: {item['ID']}, Name: {item['Name']}, "
                    f"Price: {item['Price']}, Quantity: {item['Quantity']}\n"
                )
            file.write(f"Transaction ID: {transaction_id}\n")
            file.write(f"Total cost: £{total_cost:.2f}\n")

        for item in cart.values():
            cursor.execute('''
                    INSERT INTO transactions (transaction_id, product_id, name, price, quantity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (transaction_id, item['ID'], item['Name'], item['Price'], item['Quantity']))

            db_conn.commit()  # Commit the transaction to the database
        return transaction_id

def inv_socket(socket_conn):
    handle_command(socket_conn, "VIEW")

def exit_socket(socket_conn):
    handle_command(socket_conn, "EXIT")

def cart_socket(socket_conn):
    handle_command(socket_conn, "CART")

# GUI Functions
def open_welcome_page(conn):
    """Display the welcome page with an improved UI."""

    def restore_inventory_on_exit():
        """Restore inventory if cart is not empty and the window is closed."""
        for item_id, item in cart.items():
            inventory[item_id]["Quantity"] += item["Quantity"]
        cart.clear()  # Clear the cart
        update_inventory_file()  # Save the restored inventory to the file
        root.destroy()  # Close the application

    def open_view_page():
        welcome_frame.pack_forget()
        inventory_page(conn)
        inv_socket(conn)

    def open_cart_page():
        welcome_frame.pack_forget()
        cart = Cart()
        cart.cart_page(conn)
        cart_socket(conn)

    def open_admin_page():
        welcome_frame.pack_forget()
        open_admin(conn)

    def close_program():
        root.destroy()
        exit_socket(conn)

    # Clear existing widgets
    for widget in root.winfo_children():
        widget.destroy()

    # Create the welcome frame
    welcome_frame = tk.Frame(root, bg="#f0f0f0")
    welcome_frame.pack(fill=tk.BOTH, expand=True)

    # Welcome Title
    tk.Label(
        welcome_frame,
        text="Welcome to the Vending Machine!",
        font=("Arial", 24, "bold"),
        bg="#f0f0f0",
        fg="#333"
    ).pack(pady=20)

    # Welcome Image
    welcome_image = tk.PhotoImage(file="Images/welcome.png")  # Ensure you have this image
    tk.Label(welcome_frame, image=welcome_image, bg="#f0f0f0").pack(pady=10)

    # Buttons
    button_style = {"font": ("Arial", 14), "bg": "#4CAF50", "fg": "white", "activebackground": "#45a049", "width": 20}

    tk.Button(
        welcome_frame,
        text="View Inventory",
        command=open_view_page,
        **button_style
    ).pack(pady=10)

    tk.Button(
        welcome_frame,
        text="View Cart",
        command=open_cart_page,
        **button_style
    ).pack(pady=10)

    tk.Button(
        welcome_frame,
        text="Admin",
        command=open_admin_page,
        font=("Arial", 14),
        bg="#00CCFF",
        fg="white",
        width=20,
        activebackground="#45a049"
    ).pack(pady=10)

    tk.Button(
        welcome_frame,
        text="Exit",
        command=close_program,
        font=("Arial", 14),
        bg="#f44336",
        fg="white",
        activebackground="#d32f2f",
        width=20
    ).pack(pady=10)

    # Configure the window close protocol
    root.protocol("WM_DELETE_WINDOW", restore_inventory_on_exit)

    # Keep a reference to the image to prevent garbage collection
    welcome_frame.image = welcome_image


def open_admin(conn):
    def admin_login_page():
        """Open the Admin Login page."""
        admin_frame.pack_forget()

        login_frame = tk.Frame(root, bg="#f0f0f0")
        login_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(login_frame, text="Admin Login", font=("Arial", 20), bg="#f0f0f0").pack(pady=20)

        tk.Label(login_frame, text="Username:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        username_entry = tk.Entry(login_frame, font=("Arial", 12))
        username_entry.pack(pady=5)

        tk.Label(login_frame, text="Password:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        password_entry = tk.Entry(login_frame, show="*", font=("Arial", 12))
        password_entry.pack(pady=5)


        def validate_login():
            """Validate admin credentials."""
            username = username_entry.get()
            password = password_entry.get()

            if username == "admin" and password == "password":  # Hardcoded credentials
                login_frame.pack_forget()
                inventory_manager_page()
            else:
                messagebox.showerror("Error", "Invalid username or password")

        tk.Button(
            login_frame, text="Login", command=validate_login, font=("Arial", 12), bg="#4CAF50", fg="white", width=20
        ).pack(pady=20)

        tk.Button(
            login_frame, width=20, text="Back", command=lambda: [login_frame.pack_forget(), open_admin(conn)], font=("Arial", 12)
        ).pack(pady=10)

    def go_back():
        admin_frame.pack_forget()
        open_welcome_page(conn)

    # Admin landing page
    admin_frame = tk.Frame(root, bg="#f0f0f0")
    admin_frame.pack(fill=tk.BOTH, expand=True)

    tk.Button(admin_frame, text="Admin Login", command=admin_login_page, font=("Arial", 14), bg="#4CAF50", fg="white", width=20).pack(pady=50)
    tk.Button(admin_frame, text="Exit", command=go_back, font=("Arial", 12), bg="#FF4C4C", fg="white", width=20).pack(pady=10)

    def save_inventory(items):
        """Save inventory items to the files."""
        with open("inventory.txt", "w") as inventory_file:
            for item in items:
                inventory_file.write(
                    f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']:.2f}, Quantity: {item['Quantity']}\n"
                )
        with open("fresh_inventory.txt", "w") as fresh_file:
            for item in items:
                fresh_file.write(
                    f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']:.2f}, Quantity: {item['Quantity']}\n"
                )

    def inventory_manager_page():
        """Display the Inventory Manager page for handling out-of-stock items."""
        inventory_frame = tk.Frame(root, bg="#f0f0f0")
        inventory_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(inventory_frame, text="Inventory Manager", font=("Arial", 20), bg="#f0f0f0").pack(pady=10)

        inventory_items = []
        with open("inventory.txt", "r") as inventory_file:
            for line in inventory_file:
                parts = line.strip().split(", ")
                item = {
                    "ID": parts[0].split(": ")[1],
                    "Name": parts[1].split(": ")[1],
                    "Price": float(parts[2].split(": ")[1]),
                    "Quantity": int(parts[3].split(": ")[1]),
                }
                inventory_items.append(item)

        # Load fresh inventory for refilling
        with open("fresh_inventory.txt", "r") as fresh_file:
            fresh_items = {
                line.split(", ")[0].split(": ")[1]: int(line.split(", ")[3].split(": ")[1])
                for line in fresh_file
            }

        def add_new_item():

            def back_to_inventory():
                """Navigate back to the inventory manager page."""
                for widget in root.winfo_children():
                    widget.pack_forget()
                inventory_manager_page()

            """Page to add a new item."""
            for widget in root.winfo_children():
                widget.pack_forget()

            add_frame = tk.Frame(root, bg="#f0f0f0")
            add_frame.pack(fill=tk.BOTH, expand=True)

            tk.Label(add_frame, text="Add New Item", font=("Arial", 20), bg="#f0f0f0").pack(pady=20)
            tk.Label(add_frame, text="Name:", bg="#f0f0f0", font=("Arial", 15)).pack(pady=5)
            name_entry = tk.Entry(add_frame)
            name_entry.pack(pady=5)
            tk.Label(add_frame, text="Price:", bg="#f0f0f0", font=("Arial", 15)).pack(pady=5)
            price_entry = tk.Entry(add_frame)
            price_entry.pack(pady=5)
            tk.Label(add_frame, text="Quantity:", bg="#f0f0f0", font=("Arial", 15)).pack(pady=5)
            quantity_entry = tk.Entry(add_frame)
            quantity_entry.pack(pady=5)

            def save_new_item():
                """Save the new item."""
                try:
                    new_name = name_entry.get()
                    new_price = float(price_entry.get())
                    new_quantity = int(quantity_entry.get())
                    new_id = str(int(inventory_items[-1]["ID"]) + 1 if inventory_items else 1)

                    new_item = {"ID": new_id, "Name": new_name, "Price": new_price, "Quantity": new_quantity}
                    inventory_items.append(new_item)
                    save_inventory(inventory_items)

                    messagebox.showinfo("Success", "New item added successfully!")
                    add_new_item()
                except ValueError:
                    messagebox.showerror("Error", "Invalid input! Please check your entries.")

            tk.Button(add_frame, text="Save", command=save_new_item, bg="#4CAF50", fg="white", width=20).pack(pady=20)
            tk.Button(add_frame, text="Back", command=lambda: [back_to_inventory()], bg="#FF4C4C", fg="white", width=20).pack(pady=10)

        def remove_item():

            def back_to_inventory():
                """Navigate back to the inventory manager page."""
                for widget in root.winfo_children():
                    widget.pack_forget()
                inventory_manager_page()

            """Page to remove an item with scroll functionality and improved back navigation."""
            for widget in root.winfo_children():
                widget.pack_forget()

            remove_frame = tk.Frame(root, bg="#f0f0f0")
            remove_frame.pack(fill=tk.BOTH, expand=True)

            tk.Label(remove_frame, text="Remove Item", font=("Arial", 25), bg="#f0f0f0").pack(pady=20)

            tk.Button(
                remove_frame,
                text="Back",
                command=lambda: [back_to_inventory()],  # Replace with your back navigation function
                bg="#FF4C4C",
                fg="white",
                font=("Arial", 12),
                width=20,
            ).pack(pady=5)

            # Add a canvas and scrollbar for scrolling functionality
            canvas = tk.Canvas(remove_frame, bg="#f0f0f0")
            scrollbar = ttk.Scrollbar(remove_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Pack the canvas and scrollbar
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="top", fill="both", expand=True)

            def confirm_removal(item_id):
                """Confirm removal of an item."""
                result = messagebox.askyesno("Confirm", "Are you sure you want to remove this item?")
                if result:
                    nonlocal inventory_items
                    inventory_items = [item for item in inventory_items if item["ID"] != item_id]
                    save_inventory(inventory_items)
                    messagebox.showinfo("Success", "Item removed successfully!")
                    remove_item()

            def on_enter(event):
                """Change the box color on hover."""
                event.widget.config(bg="#FF8485")

            def on_leave(event):
                """Revert the box color when hover ends."""
                event.widget.config(bg="#d9d9d9")

            # Create the grid
            row, col = 0, 0
            for item_id, item in inventory.items():
                label = tk.Label(
                    scrollable_frame,
                    text=item["Name"],
                    font=("Arial", 13),
                    bg="#d9d9d9",  # Default grey background
                    fg="black",  # Black text
                    width=27,
                    height=5,
                    relief="raised",
                    bd=2,
                )
                label.grid(row=row, column=col, padx=10, pady=10)

                # Bind hover and click events
                label.bind("<Enter>", on_enter)
                label.bind("<Leave>", on_leave)
                label.bind("<Button-1>", lambda e, i=item_id: confirm_removal(i))

                col += 1
                if col > 4:  # Adjust grid width (e.g., 5 items per row)
                    col = 0
                    row += 1


        def edit_item_page():

            def back_to_inventory():
                """Navigate back to the inventory manager page."""
                for widget in root.winfo_children():
                    widget.pack_forget()
                inventory_manager_page()

            """Page to edit an item with a grid layout and hover effects."""
            for widget in root.winfo_children():
                widget.pack_forget()

            edit_frame = tk.Frame(root, bg="#f0f0f0")
            edit_frame.pack(fill=tk.BOTH, expand=True)

            # Header
            tk.Label(edit_frame, text="Edit Item", font=("Arial", 25), bg="#f0f0f0").pack(pady=20)

            # Create a scrollable canvas for the grid
            canvas = tk.Canvas(edit_frame, bg="#f0f0f0")
            scrollbar = ttk.Scrollbar(edit_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            def go_to_edit_page(item_id):
                """Navigate to the item-specific editing page."""
                # Retrieve the specific item details from the inventory using item_id
                item = inventory[item_id]

                for widget in root.winfo_children():
                    widget.pack_forget()

                edit_page = tk.Frame(root, bg="#f0f0f0")
                edit_page.pack(fill=tk.BOTH, expand=True)

                # Display item details for editing
                tk.Label(edit_page, text=f"Editing Item ID: {item['ID']}", bg="#f0f0f0", font=("Arial", 20)).pack(
                    pady=20)
                tk.Label(edit_page, text="Name:", bg="#f0f0f0").pack(pady=5)

                name_entry = tk.Entry(edit_page)
                name_entry.insert(0, item["Name"])  # Pre-fill with current name
                name_entry.pack(pady=5)

                tk.Label(edit_page, text="Price:", bg="#f0f0f0").pack(pady=5)

                price_entry = tk.Entry(edit_page)
                price_entry.insert(0, str(item["Price"]))  # Pre-fill with current price
                price_entry.pack(pady=5)

                def save_edit():
                    """Save changes to the item."""
                    item["Name"] = name_entry.get()
                    try:
                        item["Price"] = float(price_entry.get())
                        save_inventory(inventory.values())  # Save updated inventory to file
                        messagebox.showinfo("Success", "Item edited successfully!")
                        edit_item_page()  # Navigate back to the edit item grid
                    except ValueError:
                        messagebox.showerror("Error", "Invalid price format!")

                tk.Button(
                    edit_page, text="Save", command=save_edit, bg="#4CAF50", fg="white", font=("Arial", 12), width=20
                ).pack(pady=20)

                tk.Button(
                    edit_page, text="Back", command=edit_item_page, bg="#FF4C4C", fg="white", font=("Arial", 12),
                    width=20
                ).pack(pady=10)

            def on_enter(event):
                """Change the box color on hover."""
                event.widget.config(bg="#dff0d8")

            def on_leave(event):
                """Revert the box color when hover ends."""
                event.widget.config(bg="#d9d9d9")

            # Create the grid
            row, col = 0, 0
            for item_id, item in inventory.items():
                label = tk.Label(
                    scrollable_frame,
                    text=item["Name"],
                    font=("Arial", 13),
                    bg="#d9d9d9",  # Default grey background
                    fg="black",  # Black text
                    width=27,
                    height=5,
                    relief="raised",
                    bd=2,
                )
                label.grid(row=row, column=col, padx=10, pady=10)

                # Bind hover and click events
                label.bind("<Enter>", on_enter)
                label.bind("<Leave>", on_leave)
                label.bind("<Button-1>", lambda e, i=item_id: go_to_edit_page(i))

                col += 1
                if col > 4:  # Adjust grid width (e.g., 5 items per row)
                    col = 0
                    row += 1

            # Back button
            tk.Button(
                edit_frame,
                text="Back",
                command=lambda: [back_to_inventory()],  # Replace with your back navigation function
                bg="#FF4C4C",
                fg="white",
                font=("Arial", 12),
                width=10,
            ).pack(pady=20)

        def refill_item(item_id):
            """Refill stock for a selected item."""
            for item in inventory_items:
                if item["ID"] == item_id and item["ID"] in fresh_items:
                    if item["Quantity"] == 0:
                        item["Quantity"] = fresh_items[item_id]
                        messagebox.showinfo("Success", f"{item['Name']} stock has been refilled!")
                    else:
                        messagebox.showwarning("Warning", f"{item['Name']} is not out of stock.")
                    break

            # Save updated inventory to file
            with open("inventory.txt", "w") as inventory_file:
                for item in inventory_items:
                    inventory_file.write(
                        f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']:.2f}, Quantity: {item['Quantity']}\n"
                    )

            # Refresh the inventory manager page
            inventory_frame.pack_forget()
            inventory_manager_page()

        # Display out-of-stock items
        if not any(item["Quantity"] == 0 for item in inventory_items):
            tk.Label(inventory_frame, text="No items are out of stock.", bg="#f0f0f0", font=("Arial", 14)).pack(pady=20)
        else:
            for item in inventory_items:
                if item["Quantity"] == 0:
                    item_frame = tk.Frame(inventory_frame, bg="#f0f0f0", pady=5)
                    item_frame.pack(fill="x")

                    tk.Label(
                        item_frame,
                        text=f"ID: {item['ID']} | Name: {item['Name']} | Quantity: {item['Quantity']}",
                        bg="#f0f0f0",
                        font=("Arial", 12),
                    ).pack(side="left", padx=10)

                    tk.Button(
                        item_frame,
                        text="Refill Stock",
                        command=lambda id=item["ID"]: refill_item(id),
                        bg="#4CAF50",
                        fg="white",
                        font=("Arial", 10),
                        width=12,
                    ).pack(side="right", padx=10)

        tk.Button(
            inventory_frame, text="Add New Item", command=lambda: [add_new_item()], font=("Arial", 12), bg="#4CAF50", fg="white", width=10
        ).pack(pady=20)

        tk.Button(
            inventory_frame, text="Remove Item", command=lambda: [remove_item()], font=("Arial", 12), bg="#FF4C4C", fg="white", width=10
        ).pack(pady=20)

        tk.Button(
            inventory_frame, text="Edit Item", command=lambda: [edit_item_page()], font=("Arial", 12), bg="#00CCFF", fg="white", width=10
        ).pack(pady=20)

        # Logout button
        tk.Button(
            inventory_frame, text="Logout", command=lambda: [inventory_frame.pack_forget(), open_welcome_page(conn)], font=("Arial", 12), bg="#FF4C4C", fg="white", width=10
        ).pack(pady=20)

def inventory_page(conn):
    """Display the inventory with Add to Cart buttons."""

    def cart_socket(conn):
        handle_command(conn, "CART")

    def mm_socket(conn):
        handle_command(conn, "MAIN MENU")

    def add_socket(conn):
        handle_command(conn, "ADD")

    def go_back():
        """Return to the welcome page"""
        inventory_frame.pack_forget()
        open_welcome_page(conn)
        mm_socket(conn)

    def go_cart():
        """Navigate to the cart page"""
        inventory_frame.pack_forget()
        cart = Cart()
        cart.cart_page(conn)
        cart_socket(conn)

    def load_inventory_from_file():
        """Load the inventory from the inventory.txt file."""
        global inventory
        inventory = {}  # Initialize the inventory dictionary

        try:
            with open("inventory.txt", "r") as inventory_file:
                for line in inventory_file:
                    # Each line should be in the format: ID: {ID}, Name: {Name}, Price: {Price}, Quantity: {Quantity}
                    parts = line.strip().split(", ")
                    item_id = int(parts[0].split(": ")[1])
                    name = parts[1].split(": ")[1]
                    price = float(parts[2].split(": ")[1].replace("£", ""))  # Remove currency symbol if present
                    quantity = int(parts[3].split(": ")[1])

                    # Add item to the global inventory dictionary
                    inventory[item_id] = {
                        "ID": item_id,
                        "Name": name,
                        "Price": price,
                        "Quantity": quantity,
                    }
        except FileNotFoundError:
            messagebox.showerror("Error", "Inventory file not found!")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading inventory: {e}")

    def create_inventory_grid():
        """Create a grid of inventory items with hover functionality."""
        # Clear the existing grid widgets before repopulating
        for widget in inventory_frame.winfo_children():
            widget.destroy()

        def on_enter(event, item):
            """Change display when mouse enters a box."""
            label = event.widget  # Get the widget triggering the event
            label.config(text=f"£{item['Price']} | {item['Quantity']} left", bg="#dff0d8")

        def on_leave(event, item):
            """Revert display when mouse leaves a box."""
            label = event.widget
            label.config(text=item["Name"], bg="#f0f0f0")

        def on_click(item_id):
            """Handle click on a box."""
            if item_id in inventory:
                item = inventory[item_id]
                if item["Quantity"] > 0:
                    # Add to cart or update cart quantity
                    if item_id in cart:
                        cart[item_id]["Quantity"] += 1
                    else:
                        cart[item_id] = {
                            "ID": item["ID"],
                            "Name": item["Name"],
                            "Price": item["Price"],
                            "Quantity": 1,
                        }
                    inventory[item_id]["Quantity"] -= 1
                    update_inventory_file()  # Update the inventory.txt file
                    update_inventory_page()  # Refresh the inventory page with the updated data
                    messagebox.showinfo("Success", f"{item['Name']} added to cart!")

                    add_socket(conn)
                else:
                    messagebox.showwarning("Out of Stock", f"{item['Name']} is out of stock!")
            else:
                messagebox.showerror("Error", "Item not found in inventory!")

        def update_inventory_file():
            """Write the updated inventory back to the inventory.txt file."""
            with open("inventory.txt", "w") as file:
                for item in inventory.values():
                    file.write(
                        f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']:.2f}, Quantity: {item['Quantity']}\n"
                    )

        def update_inventory_page():
            """Refresh the inventory display with the most up-to-date information."""
            create_inventory_grid()  # Re-create the grid from scratch

        # Header
        tk.Label(inventory_frame, text="Inventory", font=("Arial", 25)).pack(pady=10)

        # Create a scrollable frame for the inventory grid
        canvas = tk.Canvas(inventory_frame)
        scrollable_frame = tk.Frame(canvas)
        scrollbar = ttk.Scrollbar(inventory_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Create the grid
        row, col = 0, 0
        for item_id, item in inventory.items():
            label = tk.Label(
                scrollable_frame,
                text=item["Name"],
                font=("Arial", 13),
                bg="#f0f0f0",
                width=27,
                height=5,
                relief="raised",
                bd=2,
            )
            label.grid(row=row, column=col, padx=20, pady=20)

            # Bind hover and click events
            label.bind("<Enter>", lambda e, i=item: on_enter(e, i))
            label.bind("<Leave>", lambda e, i=item: on_leave(e, i))
            label.bind("<Button-1>", lambda e, i=item_id: on_click(i))

            col += 1
            if col > 4:  # Adjust for desired grid width (e.g., 3 items per row)
                col = 0
                row += 1

        scrollable_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Back and Cart buttons
        tk.Button(inventory_frame, text="Back", command=go_back, width=7, height=5, relief="solid", bd=2, font=("Arial", 11), bg="#FF4C4C").pack(pady=5)
        tk.Button(inventory_frame, text="Cart", command=go_cart, width=7, height=5, relief="solid", bd=2, font=("Arial", 11)).pack(pady=5)

    # Create and pack the frame for inventory
    inventory_frame = tk.Frame(root)
    inventory_frame.pack(fill=tk.BOTH, expand=True)

    load_inventory_from_file()

    create_inventory_grid()  # Initially create the inventory grid

def remove_socket(conn):
    handle_command(conn, "REMOVE")

def mm_socket(conn):
    handle_command(conn, "MAIN MENU")

def checkout_socket(conn):
    handle_command(conn, "CHECKOUT")

def oc_socket(conn):
    handle_command(conn, "ORDER COMPLETE")

class Cart:

    def cart_page(self, conn):
        cart_frame = tk.Frame(root, bg="#f0f0f0")  # Match the background color
        cart_frame.pack(fill=tk.BOTH, expand=True)

        # Variable to store cart total
        cart_total_var = tk.StringVar()

        # Header
        tk.Label(
            cart_frame,
            text="Cart Summary",
            font=("Arial", 25),
            bg="#f0f0f0"
        ).pack(pady=20)

        def go_back():
            """Navigate back to the welcome page."""
            cart_frame.pack_forget()
            open_welcome_page(conn)
            mm_socket(conn)

        def clear_cart():
            """Clear the cart and update the cart summary dynamically."""
            for item_id in cart:
                inventory[item_id]["Quantity"] += cart[item_id]["Quantity"]  # Return all quantities to inventory
            cart.clear()
            update_inventory_file()
            messagebox.showinfo("Cart", "Cart has been cleared")
            refresh_cart_summary()

        def remove_item(item_id):
            """Remove an item from the cart entirely."""
            current_cart_quantity = cart[item_id]["Quantity"]
            item_name = cart[item_id]["Name"]

            inventory[item_id]["Quantity"] += current_cart_quantity
            del cart[item_id]
            update_inventory_file()
            messagebox.showinfo("Removed", f"{item_name} removed from the cart.")
            refresh_cart_summary()
            remove_socket(conn)

        def calculate_total():
            """Calculate the total price of the items in the cart."""
            return sum(item["Price"] * item["Quantity"] for item in cart.values())

        def refresh_cart_summary():
            """Refresh the cart summary with editable quantity and save mechanism."""
            for widget in cart_summary_frame.winfo_children():
                widget.destroy()

            if cart:
                for item_id, item in cart.items():
                    item_frame = tk.Frame(cart_summary_frame, bg="#ffffff", relief="groove", bd=2)
                    item_frame.pack(pady=5, padx=10, fill=tk.X)

                    # Item details
                    tk.Label(
                        item_frame,
                        text=f"ID: {item['ID']}, Name: {item['Name']}, Price: £{item['Price']:.2f}",
                        font=("Arial", 12),
                        bg="#ffffff"
                    ).pack(side="left", padx=10)

                    # Quantity field
                    tk.Label(item_frame, text="Quantity:", bg="#ffffff", font=("Arial", 12)).pack(side="left", padx=5)
                    quantity_label = tk.Label(item_frame, text=str(item["Quantity"]), bg="#ffffff", font=("Arial", 12))
                    quantity_label.pack(side="left", padx=5)

                    # Edit Quantity Button
                    tk.Button(
                        item_frame,
                        text="Edit Quantity",
                        command=lambda item_id=item['ID']:
                        enable_edit_global(item_id),
                        bg="#FFA500",
                        fg="white",
                        font=("Arial", 10)
                    ).pack(side="left", padx=5)

                    # Remove button
                    tk.Button(
                        item_frame,
                        text="Remove",
                        command=lambda item_id=item['ID']: remove_item(item_id),
                        bg="#FF4C4C",
                        fg="white",
                        font=("Arial", 10)
                    ).pack(side="right", padx=5)
            else:
                tk.Label(
                    cart_summary_frame,
                    text="Your cart is empty!",
                    font=("Arial", 14),
                    bg="#f0f0f0"
                ).pack(pady=20)

            # Update the cart total display
            cart_total_var.set(f"Total: £{calculate_total():.2f}")

        def enable_edit_global(item_id):
            """Enable a global edit row for updating the quantity of an item."""
            # Clear any existing edit row
            for widget in cart_summary_frame.winfo_children():
                if getattr(widget, "is_edit_row", False):  # Custom attribute to mark the edit row
                    widget.destroy()

            # Create a new edit row
            edit_row_frame = tk.Frame(cart_summary_frame, bg="#ffffff", relief="groove", bd=2)
            edit_row_frame.is_edit_row = True  # Mark this frame as the edit row
            edit_row_frame.pack(pady=5, padx=10, fill=tk.X)

            # Display the item details being edited
            tk.Label(
                edit_row_frame,
                text=f"Editing Item: {cart[item_id]['Name']} (Current Quantity: {cart[item_id]['Quantity']})",
                font=("Arial", 12),
                bg="#ffffff"
            ).pack(side="left", padx=10)

            # Entry for the new quantity
            quantity_entry = tk.Entry(edit_row_frame, width=5)
            quantity_entry.insert(0, cart[item_id]["Quantity"])  # Pre-fill with current quantity
            quantity_entry.pack(side="left", padx=5)

            # Save button to update the quantity
            tk.Button(
                edit_row_frame,
                text="Save",
                command=lambda: update_quantity(item_id, quantity_entry, edit_row_frame),
                bg="#4CAF50",
                fg="white",
                font=("Arial", 10)
            ).pack(side="left", padx=5)

            # Cancel button to remove the edit row
            tk.Button(
                edit_row_frame,
                text="Cancel",
                command=lambda: edit_row_frame.destroy(),
                bg="#FF4C4C",
                fg="white",
                font=("Arial", 10)
            ).pack(side="left", padx=5)

        def cart_leave_to_payment():
            cart_frame.pack_forget()
            order = Order()
            order.payment_sim(conn)
            checkout_socket(conn)

        def update_quantity(item_id, quantity_entry, edit_row_frame):
            """Update the inventory and cart when Save button is pressed."""
            try:
                new_quantity = int(quantity_entry.get())
                if new_quantity < 0:
                    messagebox.showerror("Invalid Input", "Quantity cannot be less than 0.")
                    quantity_entry.delete(0, tk.END)
                    quantity_entry.insert(0, cart[item_id]["Quantity"])
                    return

                original_quantity = cart[item_id]["Quantity"]
                item_name = cart[item_id]["Name"]

                if new_quantity < original_quantity:
                    inventory[item_id]["Quantity"] += (original_quantity - new_quantity)
                    cart[item_id]["Quantity"] = new_quantity
                    messagebox.showinfo("Updated", f"{item_name} quantity reduced in the cart.")
                elif new_quantity > original_quantity:
                    additional_needed = new_quantity - original_quantity
                    if inventory[item_id]["Quantity"] >= additional_needed:
                        inventory[item_id]["Quantity"] -= additional_needed
                        cart[item_id]["Quantity"] = new_quantity
                        messagebox.showinfo("Updated", f"{item_name} quantity increased in the cart.")
                    else:
                        messagebox.showerror("Insufficient Stock", f"Not enough stock for {item_name}.")
                        quantity_entry.delete(0, tk.END)
                        quantity_entry.insert(0, original_quantity)
                        return

                update_inventory_file()
                edit_row_frame.destroy()
                refresh_cart_summary()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number for the quantity.")

        # Scrollable frame for the cart summary
        canvas = tk.Canvas(cart_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(cart_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        cart_summary_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        cart_summary_frame.pack()

        # Display the initial cart summary
        refresh_cart_summary()

        # Buttons
        button_frame = tk.Frame(cart_frame, bg="#f0f0f0")
        button_frame.pack(pady=20, fill=tk.X)

        tk.Button(
            button_frame,
            text="Back",
            command=go_back,
            bg="#FF4C4C",
            fg="white",
            font=("Arial", 12),
            width=12
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="Clear Cart",
            command=clear_cart,
            bg="#FFA500",
            fg="white",
            font=("Arial", 12),
            width=12
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="Complete Order",
            command=lambda: cart_leave_to_payment() if cart else messagebox.showwarning("Cart Empty",
                                                                                          "Your cart is empty."),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12),
            width=12
        ).pack(side="right", padx=10)

        # Divider and Total Price Display
        divider = tk.Frame(cart_frame, height=2, bg="#cccccc")
        divider.pack(fill=tk.X, pady=5)

        total_frame = tk.Frame(cart_frame, bg="#f0f0f0")
        total_frame.pack(side="bottom", anchor="se", pady=10, padx=20)

        tk.Label(
            total_frame,
            textvariable=cart_total_var,
            font=("Arial", 14, "bold"),
            bg="#f0f0f0"
        ).pack(side="right")

        cart_total_var.set(f"Total: £{calculate_total():.2f}")


# Update inventory file function
def update_inventory_file():
    """Write the updated inventory back to the inventory.txt file."""
    with open("inventory.txt", "w") as file:
        for item in inventory.values():
            file.write(f"ID: {item['ID']}, Name: {item['Name']}, Price: {item['Price']:.2f}, Quantity: {item['Quantity']}\n")

class Order:

    def payment_sim(self, conn):
        """Display the payment simulation page with user-entered data saved to a transaction file."""

        def is_valid_expiry_date(expiry_date):
            # Regular expression for MM/YY format (e.g. 12/25)
            pattern = r"^(0[1-9]|1[0-2])\/\d{2}$"
            return bool(re.match(pattern, expiry_date))

        def go_back():
            """Navigate back to the cart page."""
            payment_frame.pack_forget()
            cart = Cart()
            cart.cart_page(conn)  # Redirect to the cart page
            cart_socket(conn)


        def complete_payment():
            """Save payment details and complete the transaction."""
            # Get payment details
            card_number = card_number_entry.get()
            expiry_date = expiry_date_entry.get()
            cvv = cvv_entry.get()

            selected_card_type = card_type_var.get()
            if selected_card_type == 0:  # Ensure exactly one card type is selected
                messagebox.showwarning("Card Type Selection", "Please select exactly one card type.")
                return

            card_type = {1: "Visa", 2: "Mastercard", 3: "American Express"}.get(selected_card_type)

            # Check if all fields are filled
            if not card_number or not expiry_date or not cvv:
                messagebox.showwarning("Incomplete Payment", "Please fill out all payment details.")
                return

            if len(str(card_number)) > 17 or len(str(card_number)) < 16:
                messagebox.showwarning("Incorrect Card Number", "Please check the length of your card number.")
                return

            if len(str(cvv_entry)) > 4:
                messagebox.showwarning("Incorrect CVV Number", "Please check the length of your cvv.")
                return


            if not card_number.isdigit() or not cvv.isdigit():
                messagebox.showwarning("Incorrect Format", "Incorrect format for information. Please only enter digits.")
                return

            if not is_valid_expiry_date(expiry_date):
                messagebox.showwarning("Incorrect Format", "Incorrect format, expiry date must be 'MM/YY'.")
                return

            # Generate a unique transaction ID
            transaction_id = str(uuid.uuid4())

            # Calculate total cost
            total_cost = sum(item['Price'] * item['Quantity'] for item in cart.values())

            # Save transaction details to a file
            with open(TRANSACTION_FILE, "a") as file:
                file.write(f"\n\nTransaction ID: {transaction_id}\n")
                file.write(f"Payment Type: {card_type}\n")
                file.write(f"Card Number: {card_number}\n")
                file.write(f"Expiry Date: {expiry_date}\n")
                file.write(f"CVV: {cvv}\n")
                file.write(f"Cart Total: £{total_cost:.2f}\n")
                file.write("Cart Items:\n")
                for item in cart.values():
                    file.write(f"  - ID: {item['ID']}, Name: {item['Name']}, Quantity: {item['Quantity']}, "
                               f"Total: £{item['Price'] * item['Quantity']:.2f}\n")
                file.write("\n")  # Separate each transaction for readability
                oc_socket(conn)

            # Update inventory
            with open(INVENTORY_FILE, "r") as file:
                inventory_data = [line.strip() for line in file.readlines()]

            updated_inventory = []
            for line in inventory_data:
                parts = line.split(", ")
                item_id = parts[0].split(": ")[1]
                name = parts[1].split(": ")[1]
                price = float(parts[2].split(": ")[1])
                quantity = int(parts[3].split(": ")[1])  # Extract numeric value from "Quantity:"

                # Adjust inventory based on cart items
                if item_id in cart:
                    ordered_quantity = cart[item_id]['Quantity']
                    quantity -= ordered_quantity
                    quantity = max(quantity, 0)  # Ensure inventory does not go negative

                updated_inventory.append(f"ID: {item_id}, Name: {name}, Price: {price:.2f}, Quantity: {quantity}")

            with open(INVENTORY_FILE, "w") as file:
                file.write("\n".join(updated_inventory))

            # Clear the cart
            cart.clear()
            messagebox.showinfo("Payment", f"Payment completed successfully! Transaction ID: {transaction_id}")

            # Redirect to the home page
            payment_frame.pack_forget()
            open_welcome_page(conn)

        # Create the main payment frame
        # Create the main payment frame
        payment_frame = tk.Frame(root, bg="#f5f5f5")
        payment_frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas and a scrollable frame
        canvas = tk.Canvas(payment_frame, bg="#f5f5f5", highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")
        scrollbar = ttk.Scrollbar(payment_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Add the scrollable frame to the canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="n")

        scrollable_frame.columnconfigure(0, weight=1)

        # Centering container frame inside scrollable_frame
        container = tk.Frame(scrollable_frame, bg="#f5f5f5", padx=20, pady=20)
        container.pack(pady=50, padx=50, anchor="center")

        # Page Title
        tk.Label(container, text="Payment Page", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#333").pack(pady=10)

        # Cart Summary Section
        tk.Label(container, text="Cart Summary", font=("Arial", 14, "bold"), bg="#f5f5f5", fg="#555").pack(pady=10)

        if cart:
            for item in cart.values():
                tk.Label(
                    container,
                    text=f"ID: {item['ID']}, Name: {item['Name']}, Quantity: {item['Quantity']}, "
                         f"Total: £{item['Price'] * item['Quantity']:.2f}",
                    bg="#f5f5f5",
                    fg="#333",
                    font=("Arial", 12)
                ).pack(pady=5)
            total_cost = sum(item['Price'] * item['Quantity'] for item in cart.values())
            tk.Label(container, text=f"Cart Total: £{total_cost:.2f}", font=("Arial", 12, "bold"), bg="#f5f5f5",
                     fg="#333").pack(pady=10)
        else:
            tk.Label(container, text="Your cart is empty!", font=("Arial", 12), bg="#f5f5f5", fg="#777").pack()

        # Card Type Selection
        card_type_var = IntVar()
        tk.Label(container, text="Select Card Type:", font=("Arial", 12), bg="#f5f5f5", fg="#333").pack(pady=5, anchor="w")
        tk.Radiobutton(container, text="Visa", variable=card_type_var, value=1, bg="#f5f5f5", fg="#333",
                       font=("Arial", 11)).pack(anchor="w")
        tk.Radiobutton(container, text="Mastercard", variable=card_type_var, value=2, bg="#f5f5f5", fg="#333",
                       font=("Arial", 11)).pack(anchor="w")
        tk.Radiobutton(container, text="American Express", variable=card_type_var, value=3, bg="#f5f5f5", fg="#333",
                       font=("Arial", 11)).pack(anchor="w")

        # Payment Fields
        tk.Label(container, text="Card Number:", font=("Arial", 12), bg="#f5f5f5", fg="#333").pack(pady=5, anchor="w")
        card_number_entry = tk.Entry(container)
        card_number_entry.pack(pady=5, fill=tk.X)

        tk.Label(container, text="Expiry Date (MM/YY):", font=("Arial", 12), bg="#f5f5f5", fg="#333").pack(pady=5,
                                                                                                           anchor="w")
        expiry_date_entry = tk.Entry(container)
        expiry_date_entry.pack(pady=5, fill=tk.X)

        tk.Label(container, text="CVV:", font=("Arial", 12), bg="#f5f5f5", fg="#333").pack(pady=5, anchor="w")
        cvv_entry = tk.Entry(container, show="*")
        cvv_entry.pack(pady=5, fill=tk.X)

        # Button Section
        button_frame = tk.Frame(container, bg="#f5f5f5", pady=20)
        tk.Button(button_frame, text="Back", command=go_back, bg="#FF4C4C", fg="white", font=("Arial", 10, "bold")).pack(
            side="left", padx=10)
        tk.Button(button_frame, text="Complete Payment", command=complete_payment, bg="#4CAF50", fg="white",
                  font=("Arial", 10, "bold")).pack(side="right", padx=10)
        button_frame.pack(fill=tk.X)

        # Update the scroll region
        container.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))


def get_product_list():
    """Return the list of all products."""
    product_list = "\n".join(
        [
            f"ID: {item['ID']}, Name: {item['Name']}, Price: £{item['Price']:.2f}, Stock: {item['Quantity']}"
            for item in inventory.values()
        ]
    )
    return product_list if product_list else "No products available."

# Step 1: Read data from the text file
def read_data_from_file(filename):
    data = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                # Parse each line into a dictionary (ID, Name, Price, Quantity)
                parts = line.strip().split(", ")
                product = {}
                for part in parts:
                    key, value = part.split(": ")
                    product[key.strip()] = value.strip()
                data.append(product)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
    return data


# Step 2: Create and set up the database
def create_vending_machine_db():
    db_conn = sqlite3.connect('vending_machine.db')  # Create or connect to a database
    cursor = db_conn.cursor()

    # Create a table for the vending machine products
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        name TEXT PRIMARY KEY,
        transaction_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL
    )
    ''')

    db_conn.commit()  # Commit changes
    return db_conn, cursor

# Step 3: Insert data into the database
def insert_data_into_db(data, cursor):
    for product in data:
        # Insert data into the 'products' table
        cursor.execute('''
        INSERT OR IGNORE INTO products (id, name, price, quantity) VALUES (?, ?, ?, ?)
        ''', (product['ID'], product['Name'], float(product['Price']), int(product['Quantity'])))

    cursor.connection.commit()  # Commit changes to the database

def insert_transaction_into_db(data, cursor):
    for cart in data:
        # Insert data into the 'products' table
        cursor.execute('''
        INSERT INTO transactions (product_id, product_name, price, quantity) VALUES (?, ?, ?, ?)
        ''', (cart['ID'], cart['Name'], float(cart['Price']), int(cart['Quantity'])))

    cursor.connection.commit()  # Commit changes to the database


# Main function to integrate all steps
def mainsqlsetup():
    filename = 'inventory.txt'
    data = read_data_from_file(filename)

    if data:
        db_conn, cursor = create_vending_machine_db()
        insert_data_into_db(data, cursor)
    else:
        db_conn, cursor = create_vending_machine_db()

    return db_conn, cursor

def start_vending_machine(root):
    """Set up and run the vending machine GUI."""
    sql_conn, cursor = mainsqlsetup()
    product = Product()
    product.load_inventory()

    open_welcome_page(sql_conn)
    root.mainloop()  # Use the existing root instance

    sql_conn.close()

if __name__ == "__main__":
    # Initialize the root window
    root = tk.Tk()
    root.title("Vending Machine")
    root.geometry("500x400")

    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True  # This ensures the thread exits when the main program exits
    server_thread.start()

    # Start the vending machine GUI in the main thread, passing the existing root window
    start_vending_machine(root)



