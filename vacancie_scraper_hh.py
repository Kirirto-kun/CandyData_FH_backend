import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import fake_useragent
from bs4 import BeautifulSoup
import re


def fetch_page(url, headers):
    try:
        res = requests.get(url, headers=headers)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_vacancy_links(text):
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}

    base_url = f"https://hh.kz/search/vacancy?text={text}&area=40&fromSearchLine=true&search_period=0"
    print(base_url)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for page in range(40):
            url = f"{base_url}&page={page}"
            futures.append(executor.submit(fetch_page, url, headers))

        links = []
        for future in as_completed(futures):
            # print(1)
            content = future.result()
            if content:
                # print(1)
                soup = BeautifulSoup(content, "lxml")
                for a in soup.find_all(class_="magritte-link___b4rEM_4-3-2 magritte-link_style_neutral___iqoW0_4-3-2 magritte-link_enable-visited___Biyib_4-3-2"):
                    link = a["href"]
                    links.append(link)

    return links


def fetch_vacancy(link, headers):
    try:
        res = requests.get(link, headers=headers)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {link}: {e}")
        return None


def get_vacancy(link):
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}
    content = fetch_vacancy(link, headers)
    if not content:
        return None

    soup = BeautifulSoup(content, "lxml")

    try:
        title = soup.find(attrs={"data-qa": "vacancy-title"}).text.strip()
    except AttributeError:
        title = None
    try:
        experience = soup.find(attrs={"data-qa": "vacancy-experience"}).text.strip()
    except AttributeError:
        experience = None
    try:
        salary = soup.find(attrs={"data-qa": "vacancy-salary-compensation-type-net"}).text.strip()
    except AttributeError:
        salary = None

    try:
        company = soup.find(attrs={"data-qa": "vacancy-company-name"}).text.strip()
    except AttributeError:
        company = None

    try:
        description = soup.find(attrs={"data-qa": "vacancy-description"}).text.strip()
    except AttributeError:
        description = None

    vacancy = {
        "title": title,
        "experience": experience,
        "salary": salary,
        "company": company,
        "description": description,
        "link": link
    }

    return vacancy


def get_vacancies(text):
    links = get_vacancy_links(text)
    print(len(links))
    print(links)
    # return
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}

    vacancies = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_vacancy, link) for link in links]

        for future in as_completed(futures):
            vacancy = future.result()
            if vacancy:
                vacancies.append(vacancy)

    return vacancies


if __name__ == "__main__":
    text = "Программист"  # Замени на нужную профессию
    vacancies = get_vacancies(text)
    print(json.dumps(vacancies, ensure_ascii=False, indent=4))