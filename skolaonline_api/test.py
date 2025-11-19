import requests
from bs4 import BeautifulSoup

# URL of the login page (the ReturnUrl will redirect you after login)
login_url = "https://www.skolaonline.cz/prihlaseni/?ReturnUrl=ISOL%2fISOLApp%2fDefault.aspx"

# Start a session so cookies persist
session = requests.Session()

# Set a desktop user‑agent; some servers block default Python agents
headers = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/114.0 Safari/537.36")
}

# 1) GET the login page to obtain hidden ASP.NET tokens
resp = session.get(login_url, headers=headers)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

def get_hidden_value(name):
    element = soup.find("input", {"name": name})
    return element["value"] if element else ""

# Extract hidden values; adjust names if the form uses different IDs
viewstate      = get_hidden_value("__VIEWSTATE")
viewstategen   = get_hidden_value("__VIEWSTATEGENERATOR")
eventvalidation= get_hidden_value("__EVENTVALIDATION")

# Determine the actual names of the username/password fields
# You can inspect the HTML (using BeautifulSoup) to find them.
username_field = "ctl00$ContentPlaceHolder$Login1$UserName"
password_field = "ctl00$ContentPlaceHolder$Login1$Password"
button_name    = "ctl00$ContentPlaceHolder$Login1$LoginButton"

payload = {
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": viewstategen,
    "__EVENTVALIDATION": eventvalidation,
    username_field: "YOUR_USERNAME",
    password_field: "YOUR_PASSWORD",
    button_name: "Přihlásit",  # label of the login button
    # If the form has a “remember me” checkbox, include it (e.g. "ctl00$ContentPlaceHolder$Login1$RememberMe": "on")
}

# 2) POST the login request
post_resp = session.post(login_url, data=payload, headers=headers)
post_resp.raise_for_status()

# 3) After login, request the page with the data (from the ReturnUrl)
data_url = "https://aplikace.skolaonline.cz/ISOL/ISOLApp/Default.aspx"
data_resp = session.get(data_url, headers=headers)
data_resp.raise_for_status()

# 4) Parse data_resp.text with BeautifulSoup, lxml or pandas as needed
print(data_resp.text[:1000])  # Example: print first 1 000 characters