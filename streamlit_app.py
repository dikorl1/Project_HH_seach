# Открываем для теста страницу http://localhost:8502/
from openai import OpenAI
from parse_hh import get_html, extract_vacancy_data, extract_resume_data
import requests

# Словарь ключевых слов для автоматического выделения soft-skills
soft_skills_keywords = {
    "Коммуникативные навыки": ["коммуникац", "общени", "ведение переговоров", "презентац"],
    "Лидерство": ["лидер", "руководств", "team lead", "менеджер проекта"],
    "Стрессоустойчивость": ["стрессоустойчив", "устойчивость к стресс", "спокойств"],
    "Инициативность": ["инициатив", "самостоятельн", "предлагал иде"],
    "Креативность": ["креатив", "творчес", "генераци ид"],
    "Работа в команде": ["работе в команд", "teamwork", "сотрудничал"],
    "Адаптивность": ["адаптивн", "гибк", "быстро адаптироваться"],
}

def extract_soft_skills(resume_text: str):
    found = []
    text_lower = resume_text.lower()
    for skill_name, keywords in soft_skills_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(skill_name)
                break
    return list(set(found))

# Читаем OpenAI-ключ из secrets.toml
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("API-ключ не найден в st.secrets['OPENAI_API_KEY']! Проверьте файл secrets.toml.")
    st.stop()

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
Проскорь кандидата, насколько он подходит для данной вакансии.
Сначала напиши короткий анализ, который будет пояснять оценку.
Отдельно оцени качество заполнения резюме (понятно ли, с какими задачами сталкивался кандидат и каким образом их решал?). 
Эта оценка должна учитываться при выставлении финальной оценки – нам важно нанимать таких кандидатов, которые могут рассказать про свою работу.
Потом представь результат в виде оценки от 1 до 10.
""".strip()

def request_gpt(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0,
    )
    return response.choices[0].message.content

st.title("CV Scoring App")

# Поле для ссылки на вакансию
job_url = st.text_area("1) Введите ссылку на вакансию hh.ru")

# Блок для генерации / редактирования критериев
st.header("🔧 Критерии для оценки кандидата")
if "criteria_raw" not in st.session_state:
    st.session_state["criteria_raw"] = ""
if st.button("Сгенерировать критерии из вакансии"):
    job_url_str = job_url.strip()
    if not job_url_str.lower().startswith("http"):
        st.warning("Сначала вставьте ссылку на вакансию")
    else:
        job_html = get_html(job_url_str).text
        job_md = extract_vacancy_data(job_html)
        prompt_for_criteria = (
            f"Ниже текст вакансии (Markdown):\n\n{job_md}\n\n"
            "Сгенерируй 5–7 ключевых критериев для оценки кандидата (по одному на строку)."
        )
        criteria_from_gpt = request_gpt(SYSTEM_PROMPT, prompt_for_criteria)
        st.session_state["criteria_raw"] = criteria_from_gpt

criteria_raw = st.text_area(
    label="Ключевые критерии (по одному на строку)",
    value=st.session_state.get("criteria_raw", ""),
    height=150
)
criteria_list = [line.strip("• ").strip() for line in criteria_raw.splitlines() if line.strip()]

# Поле для резюме (plain-text)
resume_input = st.text_area("2) Введите текст резюме (копируйте из браузера)")

if st.button("Проанализировать соответствие"):
    with st.spinner("Парсим данные и отправляем в GPT..."):
        try:
            # 1) Парсим вакансию
            job_url_str = job_url.strip()
            if not job_url_str.lower().startswith("http"):
                st.error("Поле «ссылка на вакансию» должно начинаться с http:// или https://")
                st.stop()
            job_html = get_html(job_url_str).text
            job_text = extract_vacancy_data(job_html)

            # 2) Здесь: резюме — plain-text (пользователь вставил уже готовый текст)
            resume_text = resume_input.strip()
            if not resume_text:
                st.error("Пожалуйста, вставьте текст резюме (plain-text), а не ссылку.")
                st.stop()

            # 3) Выделяем soft-skills
            soft_skills_found = extract_soft_skills(resume_text)
            soft_block = ""
            if soft_skills_found:
                soft_block = "## SOFT-SKILLS (выявленные):\n" + \
                             "\n".join(f"- {s}" for s in soft_skills_found) + "\n\n"

            # 4) Формируем блок критериев
            criteria_block = ""
            if criteria_list:
                criteria_block = "## КРИТЕРИИ ДЛЯ ОЦЕНКИ:\n" + \
                                 "\n".join(f"- {c}" for c in criteria_list) + "\n\n"

            # 5) Собираем единый prompt
            prompt = (
                f"{criteria_block}"
                f"# ВАКАНСИЯ\n{job_text}\n\n"
                f"{soft_block}"
                f"# РЕЗЮМЕ\n{resume_text}"
            )

            response = request_gpt(SYSTEM_PROMPT, prompt)
            st.subheader("📊 Результат анализа:")
            st.markdown(response)

            # 6) Показываем найденные soft-skills под результатом
            if soft_skills_found:
                st.markdown("**Найденные soft-skills:** " + ", ".join(soft_skills_found))

        except Exception as e:
            st.error(f"Произошла ошибка: {e}")
