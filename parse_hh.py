# Открываем для теста страницу http://localhost:8502/import requests
from bs4 import BeautifulSoup

def get_html(url):
    """
    Возвращает объект Response для заданного URL, подставляя подробные HTTP-заголовки,
    имитирующие реальный браузер. Если статус-код отличный от 200, возбуждает HTTPError.
    """
    headers = {
        # Строка User-Agent полностью имитирует современный браузер Chrome/Edge
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82"
        ),
        # Дополнительные заголовки, которые обычно отправляет браузер
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://hh.ru/",  # указываем реферер, чтобы казалось, что запрос идет со страницы hh.ru
        "Upgrade-Insecure-Requests": "1",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # если код отличен от 200, выбросит HTTPError
    return response

def extract_vacancy_data(html):
    soup = BeautifulSoup(html, 'html.parser')

    def safe_text(selector, attrs=None):
        el = soup.find(selector, attrs or {})
        return el.text.strip() if el else "Не найдено"

    title = safe_text('h1')
    salary = safe_text('span', {'data-qa': 'vacancy-salary'})
    company = safe_text('a', {'data-qa': 'vacancy-company-name'})
    description_el = soup.find('div', {'data-qa': 'vacancy-description'})
    description_text = (
        description_el.get_text(separator="\n").strip()
        if description_el else
        "Описание не найдено"
    )

    markdown = f"# {title}\n\n"
    markdown += f"**Компания:** {company}\n\n"
    markdown += f"**Зарплата:** {salary}\n\n"
    markdown += f"## Описание\n\n{description_text}"
    return markdown.strip()

def extract_resume_data(html):
    soup = BeautifulSoup(html, 'html.parser')

    def safe_text(selector, **kwargs):
        el = soup.find(selector, kwargs)
        return el.text.strip() if el else "Не найдено"

    name = safe_text('h2', data_qa='bloko-header-1')
    gender_age = safe_text('p')
    location = safe_text('span', data_qa='resume-personal-address')
    job_title = safe_text('span', data_qa='resume-block-title-position')
    job_status = safe_text('span', data_qa='job-search-status')

    experiences = []
    experience_section = soup.find('div', {'data-qa': 'resume-block-experience'})
    if experience_section:
        experience_items = experience_section.find_all('div', class_='resume-block-item-gap')
        for item in experience_items:
            try:
                period_el = item.find('div', class_='bloko-column_s-2')
                duration_el = item.find('div', class_='bloko-text')
                if period_el and duration_el:
                    period_text = period_el.text.strip()
                    duration_text = duration_el.text.strip()
                    period = period_text.replace(duration_text, f"{duration_text}")
                else:
                    period = "Не указано"

                company_el = item.find('div', class_='bloko-text_strong')
                company = company_el.text.strip() if company_el else "Не указано"

                position_el = item.find('div', {'data-qa': 'resume-block-experience-position'})
                position = position_el.text.strip() if position_el else "Не указано"

                description_el = item.find('div', {'data-qa': 'resume-block-experience-description'})
                description = description_el.text.strip() if description_el else ""

                experiences.append(
                    f"**{period}**\n\n*{company}*\n\n**{position}**\n\n{description}\n"
                )
            except Exception:
                continue

    skills = []
    skills_section = soup.find('div', {'data-qa': 'skills-table'})
    if skills_section:
        tags = skills_section.find_all('span', {'data-qa': 'bloko-tag__text'})
        skills = [tag.text.strip() for tag in tags]

    markdown = f"# {name}\n\n"
    markdown += f"**{gender_age}**\n\n"
    markdown += f"**Местоположение:** {location}\n\n"
    markdown += f"**Должность:** {job_title}\n\n"
    markdown += f"**Статус:** {job_status}\n\n"
    markdown += "## Опыт работы\n\n"
    markdown += "\n".join(experiences) if experiences else "Опыт работы не найден.\n"
    markdown += "\n## Ключевые навыки\n\n"
    markdown += ", ".join(skills) if skills else "Навыки не указаны.\n"
    return markdown.strip()
