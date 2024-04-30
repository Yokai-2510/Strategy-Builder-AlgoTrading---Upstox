import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote, urlparse, parse_qs
import requests as rq
import pyperclip
import time
from credentials import API_KEY, SECRET_KEY, RURL

class UPSTOXManualLogin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UPSTOX Manual Login")
        self.geometry("500x400")
        self.configure(bg="#1c1c1c")

        # Create a custom style
        self.style = ttk.Style()
        self.style.configure("TLabel", background="#1c1c1c", foreground="#ffffff")
        self.style.configure("TEntry", background="#1A7620", foreground="#000000", borderwidth=0, highlightthickness=0)
        self.style.configure("SubmitButton.TButton", background="#133916", foreground="#000000", borderwidth=0, highlightthickness=0, font=("Arial", 12))

        # Change background color of SubmitButton.TButton
        self.style.map("SubmitButton.TButton",
            background=[("active", "#1A7620"), ("disabled", "#133916")]  # Active and disabled states
        )

        # Authentication URL
        self.auth_url = f'https://api-v2.upstox.com/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={quote(RURL, safe="")}'

        # GUI elements
        self.url_label = ttk.Label(self, text="Please click the button to copy the authentication URL to clipboard:")
        self.url_label.pack(pady=20)

        # Button to copy URL
        self.copy_button = ttk.Button(self, text="Copy URL", command=self.copy_url)
        self.copy_button.pack(pady=10)

        self.auth_code_label = ttk.Label(self, text="Paste the URL obtained after manual login:")
        self.auth_code_label.pack(pady=20)

        self.auth_code_entry = ttk.Entry(self, style="TEntry")  # Apply TEntry style
        self.auth_code_entry.pack(pady=10)

        self.submit_button = ttk.Button(self, text="Submit", command=self.process_auth_code, style="SubmitButton.TButton")
        self.submit_button.pack(pady=20)

    def copy_url(self):
        pyperclip.copy(self.auth_url)  # Copy URL to clipboard
        messagebox.showinfo("URL Copied", "URL copied to clipboard successfully.", parent=self)

    def process_auth_code(self):
        url = self.auth_code_entry.get()
        parsed_url = urlparse(url)
        auth_code = parse_qs(parsed_url.query).get('code', [None])[0]

        if auth_code:
            self.retrieve_access_token(auth_code)
        else:
            self.process_manual_auth_code()

    def process_manual_auth_code(self):
        auth_code = self.auth_code_entry.get()
        self.retrieve_access_token(auth_code)

    def retrieve_access_token(self, auth_code):
        # Retrieve access token
        url = 'https://api-v2.upstox.com/login/authorization/token'
        headers = {
            'accept': 'application/json',
            'Api-Version': '2.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'code': auth_code,
            'client_id': API_KEY,
            'client_secret': SECRET_KEY,
            'redirect_uri': RURL,
            'grant_type': 'authorization_code'
        }
        response = rq.post(url, headers=headers, data=data)
        if response.status_code == 200:
            json_response = response.json()
            access_token = json_response['access_token']
            with open("access_token.txt", "w") as file:
                file.write(access_token)

            # Fetch LTP (Last Traded Price) of Bank Nifty
            open_value = self.get_open_value(access_token)
            if open_value is not None:
                message = f"Access token fetched successfully.\n\nBank Nifty Current Price : {open_value}"
                messagebox.showinfo("Access Token & LTP", message, parent=self)
                self.countdown_before_exit()
        else:
            messagebox.showerror("Error", "Failed to fetch access token. Please try again.", parent=self)

    def get_open_value(self, access_token):
        # Fetching open value from market quotes
        url = "https://api.upstox.com/v2/market-quote/quotes"
        headers = {
            'accept': 'application/json',
            'Api-Version': '2.0',
            'Authorization': f'Bearer {access_token}'
        }
        payload = {'symbol': "NSE_INDEX|Nifty Bank"}
        response = rq.get(url, headers=headers, params=payload)
        if response.status_code == 200:
            response_data = response.json()
            open_value = response_data['data']['NSE_INDEX:Nifty Bank']['ohlc']['open']
            return open_value
        else:
            return None

    def countdown_before_exit(self):
        def close_after_countdown():
            self.destroy()

        for i in range(5, 0, -1):
            if i == 5 :
                messagebox.showinfo("Exiting Application", f"The application will close in {i} seconds.", parent=self)
            self.update_idletasks()
            time.sleep(1)
        self.after(3000, close_after_countdown)  # Automatically close after 5 seconds

if __name__ == "__main__":
    app = UPSTOXManualLogin()
    app.mainloop()