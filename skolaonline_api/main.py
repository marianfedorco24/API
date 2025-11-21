from dotenv import load_dotenv
import os, requests
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

def get_date():
    response = requests.get("https://api.timezonedb.com/v2.1/get-time-zone?key=21NHSAQ7TSX4&format=json&by=zone&zone=Europe/Prague") # requests data from the API
    date = response.json()["formatted"] # selects the correct format
    date_string = date[0:10] # selects the needed part

    date_list = date_string.split("-") # splits the string into a list

    return f"{date_list[2]}.{date_list[1]}." # returns the formatted date

def main():
    date_today = get_date()

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


        for tr in tr_list:
            date_cell = tr.select_one("td.KuvHeaderText")
            if date_cell and date_cell.get_text(strip=True) == "24.11.":  # replace with date_today to get today's lessons
                # when the row is found
                lesson_cells = tr.find_all("td", recursive=False)
                for lesson_cell in lesson_cells[1:]:  # skip the first cell (0th lesson)
                    if not lesson_cell.find("span", class_="KuvBunkaRozvrhNadpis"):
                        continue  # skip empty lesson cells
                    lesson_name = lesson_cell.find("span", class_="KuvBunkaRozvrhNadpis").get_text(strip=True)
                    lesson_room = str(lesson_cell.find("span", class_="KuvBunkaRozvrhText").decode_contents()).split("<br/>")[1]
                    if len(lesson_room) > 30:
                        lesson_room = "------"
                    print(f"{lesson_name} | {lesson_room}")
                break  # exit after processing today's lessons



    finally:
        driver.quit()

main()