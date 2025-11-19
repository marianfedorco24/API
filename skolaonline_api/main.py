import requests, sys, os
from json import loads
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
LOGIN_URL = "https://aplikace.skolaonline.cz/SOL/Prihlaseni.aspx"
DATA_URL = "https://aplikace.skolaonline.cz/SOL/App/Spolecne/KZZ010_RychlyPrehled.aspx"

login_data = {
    "JmenoUzivatele": USERNAME,
    "HesloUzivatele": PASSWORD,
    "btnLogin": "Přihlásit do aplikace"
}
login_headers = {
    ":authority": "aplikace.skolaonline.cz",
    ":method": "POST",
    ":path": "/SOL/Prihlaseni.aspx",
    ":scheme": "https",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,cs;q=0.8,cs-CZ;q=0.7",
    "cache-control": "max-age=0",
    "content-length": "105",
    "content-type": "application/x-www-form-urlencoded",
    "cookie": "_ga=GA1.1.86381295.1758039753; ZPUSOB_OVERENI=SOL; SOL_LOGIN=872ae3bb2412487db269b38d25d4e65b:d3984c831155be5664e204b31d676386; ASP.NET_SessionId=sug4e0qatdykdplyfvlwv0fb; SERVERID=S-WEB-02; .ASPXAUTH=F69EFBEA3207083C74B0032150A6BC1965D7D0317255F7262A5D2A4C768A8F0353CA6A67BEC58CE6E56C492DF1F59E6DA98BEE5F795CBC3059719CB19D496EE99E7EF80D94EB55B32BCA1E09D421D8184A802E8780119494C63731AB621949288734F318; SESSION_EXPIRES=2025-11-14T10:10:04; cookieconsent_sol={\"level\":[\"necessary\",\"analytics\"],\"revision\":0,\"data\":null,\"rfc_cookie\":false}; __utma=202636225.86381295.1758039753.1763109616.1763109616.1; __utmc=202636225; __utmz=202636225.1763109616.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmt=1; __utmb=202636225.1.10.1763109616; _ga_2HV2HY4W2B=GS2.1.s1763109332$o4$g1$t1763109643$j43$l0$h0",
    "origin": "https://www.skolaonline.cz",
    "priority": "u=0, i",
    "referer": "https://www.skolaonline.cz/prihlaseni/?",
    "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

def get_data_skolaonline():
    session = requests.Session()
    login_request = session.post(LOGIN_URL, json = login_data)
    print(login_request.status_code)

    data_request = session.get(DATA_URL)
    print(data_request.text)

    # data = f'{"{"}"cislo":"{CANTEEN_NUM}","sid":"{sid}","s5url":"{s5url}","lang":"EN","konto":0,"podminka":"","ignoreCert":"false"{"}"}'
    # response = requests.post(DATA_URL, data = data)

    # raw_src = loads(response.text)

    # return raw_src

def get_date():
    response = requests.get("https://api.timezonedb.com/v2.1/get-time-zone?key=21NHSAQ7TSX4&format=json&by=zone&zone=Europe/Prague") # requests data from the API
    date = response.json()["formatted"] # selects the correct format
    date_string = date[0:10] # selects the needed part

    date_list = date_string.split("-") # splits the string into a list

    return f"{date_list[2]}. {date_list[1]}. {date_list[0]}" # returns the formatted date

get_data_skolaonline()