import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import fake_useragent
from bs4 import BeautifulSoup
import re
import time


def fetch_page(url, headers):
    try:
        res = requests.get(url, headers=headers)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_links(link):
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}

    base_url = link

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for page in range(2):
            url = f"{base_url}&page={page}"
            futures.append(executor.submit(fetch_page, url, headers))

        links = []
        for future in as_completed(futures):
            content = future.result()
            if content:
                soup = BeautifulSoup(content, "lxml")
                for a in soup.find_all("a", href=re.compile("^/resume/")):
                    link = f'https://hh.kz{a.attrs["href"].split("?")[0]}'
                    if link not in links:
                        links.append(link)

    return links[:20]


def fetch_resume(link, headers):
    try:
        res = requests.get(link, headers=headers)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {link}: {e}")
        return None


def get_resume(link):
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}
    content = fetch_resume(link, headers)
    if not content:
        return None

    soup = BeautifulSoup(content, "lxml")

    id = link[21:]
    try:
        name = soup.find(attrs={"class": "resume-block__title-text"}).text.strip()
    except AttributeError:
        name = None
    try:
        salary_text = soup.find(attrs={"class": "resume-block__salary"}).text.replace("\u2009", "").replace("\xa0",
                                                                                                       " ").strip()
        salary_match = re.search(r"(\d+)", salary_text)
        if salary_match:
            salary = int(salary_match.group(1))
        else:
            salary = 0

    except AttributeError:
        salary = None

    try:
        experience_text = soup.find(attrs={"class": "resume-block__title-text_sub"}).text.replace("Опыт работы", "").replace(
            "\xa0", " ").strip()
        experience_match = re.search(r"(\d+)\s*(год|лет|year|years)", experience_text)
        if experience_match:
            experience = int(experience_match.group(1))
        else:
            experience = 0
    except AttributeError:
        experience = None

    try:
        description = soup.find(attrs={"data-qa": "resume-block-skills-content"}).text.strip()
    except AttributeError:
        description = None
    try:
        containers = soup.select('.resume-block-item-gap .bloko-columns-row .bloko-column .bloko-tag-list')
        if containers:
            container = containers[-1]
            languages = [language.get_text(separator=' ', strip=True) for language in
                         container.select('.bloko-tag_inline .bloko-tag__section_text')]
        else:
            languages = []

    except AttributeError:
        languages = []

    try:
        containers = soup.select('[data-sentry-element="ColumnsRow"]')
        expObject = []

        if containers:
            for container in containers:
                # Extract durations and remove secondary text within it
                durations = [
                    duration.text.strip().replace("\xa0", " ")
                    for duration in container.select('.bloko-column_l-2')
                ]
                durationMinuss = [
                    durationMinus.text.strip().replace("\xa0", " ")
                    for durationMinus in container.select('.bloko-column_l-2 .bloko-text_tertiary')
                ]
                cleaned_durations = [
                    duration.replace(durationMinus, '').strip()
                    for duration, durationMinus in zip(durations, durationMinuss)
                ]

                # Extract other details: company names, links, roles, and descriptions
                companyNames = [
                    companyName.text.strip()
                    for companyName in container.select('.bloko-column_l-10 .resume-block-container .bloko-text_strong')
                ]
                companyLinks = [
                    companyLink['href'].strip()
                    for companyLink in
                    container.select('.bloko-column_l-10 .resume-block-container .bloko-link_kind-tertiary')
                ]
                roles = [
                    role.text.strip()
                    for role in container.select('[data-qa="resume-block-experience-position"]')
                ]
                roleDescriptions = [
                    roleDescription.text.strip()
                    for roleDescription in container.select('[data-qa="resume-block-experience-description"]')
                ]

                # Assemble each experience item
                for i in range(len(cleaned_durations)):
                    expItem = {
                        "duration": cleaned_durations[i] if i < len(cleaned_durations) else None,
                        "companyName": companyNames[i] if i < len(companyNames) else None,
                        "companyLink": companyLinks[i] if i < len(companyLinks) else None,
                        "role": roles[i] if i < len(roles) else None,
                        "roleDescription": roleDescriptions[i] if i < len(roleDescriptions) else None,
                    }

                    # Check for duplicate entries
                    if not any(
                            d['duration'] == expItem['duration'] and
                            d['companyName'] == expItem['companyName'] and
                            d['role'] == expItem['role'] and
                            d['companyLink'] == expItem['companyLink']
                            for d in expObject
                    ):
                        expObject.append(expItem)
        if expObject:
            half_length = len(expObject) // 2
            expObject = expObject[:half_length]
        else:
            expObject = None
    except AttributeError:
        expObject = None

    try:
        container = soup.select_one(
            '.resume-block-item-gap .bloko-columns-row .bloko-column .resume-block-container .bloko-tag-list')
        tags = [tag.text for tag in
                container.find_all("span", attrs={"class": "bloko-tag__section_text"})] if container else []
    except AttributeError:
        tags = []
    resume = {
        "id": id,
        "name": name,
        "salary": salary,
        "description": description,
        "experience": experience,
        "expObject": expObject,
        "tags": tags,
        "languages": languages,
    }

    if not name or not tags:
        return None

    return resume


def get_resume_please(link):
    links = get_links(link)
    print(links)
    ua = fake_useragent.UserAgent()
    headers = {"user-agent": ua.random}

    resumes = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_resume, link) for link in links]

        for future in as_completed(futures):
            resume = future.result()
            if resume:
                resumes.append(resume)

    return resumes