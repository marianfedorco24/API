from dotenv import load_dotenv
import time, os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

LOGIN_URL = "https://www.skolaonline.cz/prihlaseni/?"

CHROMEDRIVER_PATH = None
# CHROMEDRIVER_PATH = "/usr/bin/chromedriver"   # 

def main():
    # 1) Selenium options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,720")

    # 2) Initialize WebDriver
    if CHROMEDRIVER_PATH:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    try:
        wait = WebDriverWait(driver, 15)

        # 3) Open login page
        driver.get(LOGIN_URL)

        # 4) Fill login form
        username_input = wait.until(
            EC.presence_of_element_located((By.NAME, "JmenoUzivatele"))
        )
        password_input = driver.find_element(By.NAME, "HesloUzivatele")

        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.ENTER)

        # 5) Wait for UI element that appears *after* login
        wait.until(
            EC.presence_of_element_located((By.ID, "ctl00_main_boxKalendar_ctl00_ctl04"))
        )

        # 7) Parse HTML of the timetable
        timetable = driver.find_element(By.ID, "ctl00_main_boxKalendar_ctl00_ctl04")
        html = timetable.get_attribute("innerHTML")
        soup = BeautifulSoup(html, "lxml")

        tr_list = soup.select_one("tbody").find_all("tr", recursive=False)
        print(len(tr_list))
        for tr in tr_list:
            date_cell = tr.select_one("td.KuvHeaderText")
            if date_cell and date_cell.get_text(strip=True) == "12.11.":
                print("Date match!")
                print(tr)



    finally:
        driver.quit()

main()