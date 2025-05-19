import socket
import threading
import time
import random

# Server configuration
HOST = '127.0.0.1'
PORT = 5000
BUFSIZE = 2048

# Dictionary to track user activity
user_activity = {}

client_id = random.randint(100000, 999999)  # Generate a random client ID


def track_activity(client_id, page):
    """Track the page a user accesses and the time spent."""
    start_time = time.time()

    # Calculate duration
    duration = time.time() - start_time

    # Update activity log
    user_activity[client_id] = user_activity.get(client_id, [])
    user_activity[client_id].append((page, duration))


def log_user_activity(client_id):
    """Log the activity of a user."""
    print(f"\nUser {client_id} Activity:")
    for page, start_time in user_activity.get(client_id, []):
        duration = time.time() - start_time
        print(f" - Page: {page}, Time Spent: {duration:.2f} seconds")

# Dictionary of client responses for each server command
def set_client_id(client_socket):
    """Send the client ID to the server."""
    global client_id
    client_socket.sendall(str(client_id).encode('utf-8'))
    print(f"Client ID: {client_id} set.")

def respond_to_command(command):
    """Respond to a command from the server."""
    responses = {
        "VIEW": "Inventory Page",
        "MAIN MENU": "Main Menu Page",
        "ADD": "Product Added to Cart",
        "REMOVE": "Product Removed from Cart",
        "CART": "Cart Page",
        "CHECKOUT": "Checkout Page",
        "ORDER COMPLETE": "Order Completed and Saved",
        "EXIT": "Goodbye!"
    }
    return responses.get(command.upper(), "Unknown command")

def main():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))
            print(f"Connected to server at {HOST}:{PORT}")

            set_client_id(client_socket)
            initial_response = client_socket.recv(BUFSIZE).decode('utf-8').strip()
            print(initial_response)

            while True:
                # Receive command from the server
                command = client_socket.recv(BUFSIZE).decode('utf-8').strip()
                if not command:
                    print("Server disconnected.")
                    break

                print(f"Server sent command: {command}")

                track_activity(client_id, command)

                # Get the response and send it back to the server
                response = respond_to_command(command)
                print(response)

                if command.upper() == "EXIT":
                    print("Server requested exit. Closing connection...")
                    break
    except Exception as e:
        print(f"Error in client: {e}")
    finally:
        log_user_activity(client_id)  # Log user activity when the client disconnects
        print("Client disconnected.")


if __name__ == "__main__":
    main()


