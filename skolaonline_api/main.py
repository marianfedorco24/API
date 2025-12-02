from dotenv import load_dotenv
import os, requests, re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


BASE_DIR = Path(__file__).resolve().parent  # adjust if needed
load_dotenv(BASE_DIR / ".env", override=True)

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

LOGIN_URL = "https://www.skolaonline.cz/prihlaseni/?"
class_times = ["08:00", "08:55", "10:00", "10:55", "11:50", "12:45", "14:00", "14:55"]

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

def get_date():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    return now.strftime("%-d.%-m.")

def convert_time_string(t):
    dt = datetime.strptime(t, "%H:%M").replace(
        year=datetime.today().year,
        month=datetime.today().month,
        day=datetime.today().day
    )
    return int(dt.timestamp())

def get_matching_parent_class(el, class_variants):
    parent = el.parent
    while parent is not None:
        classes = parent.get("class", [])
        # classes can be a list or a string
        if isinstance(classes, str):
            classes = classes.split()
        for cls in class_variants:
            if cls in classes:
                return cls
        parent = parent.parent
    return None

def parse_onmouseover(attr: str):
    m = re.search(r"onMouseOverTooltip\('(.*?)','(.*?)'\)", attr)
    if not m:
        return None
    
    subject, info = m.groups()
    parts = info.split("~")

    data = {"subject": subject.split(" ")[0]}

    for i in range(0, len(parts), 2):
        key = parts[i].rstrip(":")
        value = parts[i+1]
        data[key] = value

    return data

def get_today_row_class(html, date_today):
    soup = BeautifulSoup(html, "lxml")
    tr_list = soup.find_all("tr")
    # Find the row corresponding to today's date
    for tr in tr_list:
        date_cell = tr.select_one("td.KuvHeaderText")
        # Check if the date cell matches today's date
        if date_cell and date_cell.get_text(strip=True) == date_today:
            # Get all rows for today (could be multiple if there are extra rows)
            row_class = get_matching_parent_class(date_cell, ["RowOdd", "RowEven"])
            return row_class
    return None

def get_today_lessons():
    date_today = get_date()

    # 1) Selenium options
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium-browser"
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

        row_class = get_today_row_class(html, date_today)

        rows_today = timetable.find_elements(By.CSS_SELECTOR, f".{row_class}")
        lesson_cells = []
        for row in rows_today:
            lesson_cells.extend(row.find_elements(By.CLASS_NAME, "DctInnerTableType10DataTD"))
            lesson_cells.extend(row.find_elements(By.CLASS_NAME, "KuvSkolniAkceHodina"))
            lesson_cells.extend(row.find_elements(By.CLASS_NAME, "KuvSuplujiciHodina"))
        
        
        lesson_cells_sorted = sorted(lesson_cells, key=lambda el: el.location['x'])
        lessons_today = [parse_onmouseover(cell.get_attribute("onmouseover")) for cell in lesson_cells_sorted if cell.get_attribute("onmouseover")]

        for lesson in lessons_today:
            class_time = 0
            if lesson.get("Čas výuky"):
                class_time = convert_time_string(lesson["Čas výuky"].split(" - ")[0])
            else:
                class_num = lesson["Den (vyuč. hodina)"].split(" ")[-1][1]
                class_time = convert_time_string(class_times[int(class_num)-1])
            
            lesson["timestamp"] = class_time

        return lessons_today

    finally:
        driver.quit()