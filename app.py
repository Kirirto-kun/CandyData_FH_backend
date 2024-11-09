from fastapi import FastAPI, Depends, HTTPException, UploadFile, File 
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from models import *
from config import get_db, init_db
from auth_utils import hash_password, verify_password, create_access_token, verify_access_token
from datetime import timedelta
from data_scraper import get_resume_please 
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import relationship
from config import Base
import openai
import requests
import fitz
from PIL import Image
import io
import base64
from typing import List
import os
import json
import io
from pinecone import Pinecone
from openai import OpenAI
from PIL import Image
import base64
import hashlib

openai.api_key = ''

app = FastAPI()

init_db()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Or specify specific domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = file.filename
        
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
                
        return {
            "transcript": transcription
        }
    
    except Exception as e:
        return {"error": str(e)}


@app.post("/register/", response_model=dict)
def register_user(user: UserCreate, db: Session = Depends(get_db)) -> dict:
    db_user = db.query(UserInDB).filter(UserInDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)
    new_user = UserInDB(
        name=user.name,
        company_name=user.company_name,
        email=user.email,
        subscription_level="Free",
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    return {"msg": "User created successfully"}

@app.post("/login/", response_model=Token)
def login_for_access_token(user: UserLogin, db: Session = Depends(get_db)) -> Token:
    db_user = db.query(UserInDB).filter(UserInDB.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/")
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.delete("/resume/")
def delete_all_users(db: Session = Depends(get_db)):
    db.query(CandidateInDB).delete()
    db.commit()
    return {"msg": "All resumes deleted successfully"}

@app.get("/resume/")
def get_resume(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    resume_data = db.query(CandidateInDB).filter(CandidateInDB.user_id == user.id).all()

    return {"resume": [r.data for r in resume_data]}


load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

class ResumeCreate(BaseModel):
    text: str

# Функция для получения данных от GPT-4 Turbo (AI агента)
def get_link_with_gpt(description):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }
    data = {
        "messages": [
            {"role": "system", "content": "You are an assistant that generates optimized links for job searches based on user input."},
            {"role": "user", "content": f"Ты должен сгенерировать ссылку для парсинга кандидатов, ссылка должна содержать самые главные ключевые слова, не пиши много слов, только самые главные вот примеры ссылок. не пиши про навыки, убери их с ссылки, ато если будут навыки ты можешь ошибиться: https://hh.kz/search/resume?area=40&isDefaultArea=true&exp_period=all_time&logic=normal&pos=full_text&hhtmFrom=vacancy_search_list&hhtmFromLabel=resume_search_line&search_period=0&order_by=relevance&filter_exp_period=all_time&relocation=living_or_relocation&gender=unknown&experience=moreThan6&skill=231&text=c%2B%2B.  \n https://hh.kz/search/resume?area=40&isDefaultArea=true&ored_clusters=true&order_by=relevance&search_period=0&logic=normal&pos=full_text&exp_period=all_time&skill=231&hhtmFrom=resume_search_result&hhtmFromLabel=resume_search_line&filter_exp_period=all_time&job_search_status=looking_for_offers&job_search_status=active_search&job_search_status=has_job_offer&relocation=living_or_relocation&gender=unknown&experience=moreThan6&text=c%2B%2B  \n https://hh.kz/search/resume?area=40&isDefaultArea=true&ored_clusters=true&order_by=relevance&search_period=0&job_search_status=looking_for_offers&job_search_status=active_search&job_search_status=has_job_offer&logic=normal&pos=full_text&exp_period=all_time&skill=1114&hhtmFrom=resume_search_result&hhtmFromLabel=resume_search_line&filter_exp_period=all_time&relocation=living_or_relocation&gender=unknown&text=Python \n https://hh.kz/search/resume?area=40&isDefaultArea=true&ored_clusters=true&order_by=relevance&search_period=0&job_search_status=looking_for_offers&job_search_status=active_search&job_search_status=has_job_offer&logic=normal&pos=full_text&exp_period=all_time&skill=1114&skill=416&hhtmFrom=resume_search_result&hhtmFromLabel=resume_search_line&filter_exp_period=all_time&relocation=living_or_relocation&text=Python+django&gender=unknown \n Запрос: {description}, отправь только ссылку, и больше ничего"}
        ],
        "max_tokens": 250,
        "temperature": 0.5
    }
    
    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при запросе к GPT-4 Turbo")

    # Получаем текст ответа от GPT
    gpt_response = response.json()["choices"][0]["message"]["content"].strip()
    return gpt_response

def summarize_with_gpt(prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }
    data = {
        "messages": [
            {"role": "system", "content": "Тебе дается переписка между HR менеджером и человеком, ты должен скинуть что хотел человек, сделать вывод из всего что нужно человеку, детально"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.5
    }
    
    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при запросе к GPT-4 Turbo")

    # Получаем текст ответа от GPT
    gpt_response = response.json()["choices"][0]["message"]["content"].strip()
    return gpt_response

def prompt_to_gpt(prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }
    data = {
        "messages": [
            {"role": "system", "content": "Ты HR менеджер, который поможет человеку нанять лучшего кандидата. Тебе на вход дается ваша история переписки с человеком, ты задаешь дополнительные вопросы что бы лучше понять что нужно человеку, если у тебя нетe вопросов нету пишешь: Спасибо, вопросов больше нету. если у тебя неут вопросов нету пишеь: Спасибо, вопросов больше нету."},
            {"role": "user", "content": f"Ты HR менеджер, который поможет человеку нанять лучшего кандидата. Тебе на вход дается ваша история переписки с человеком, ты задаешь дополнительные вопросы что бы лучше понять что нужно человеку, если у тебя нетe вопросов нету пишешь: Спасибо, вопросов больше нету. если у тебя неут вопросов нету пишеь: Спасибо, вопросов больше нету.\n {prompt}"}
        ],
        "max_tokens": 1000,
        "temperature": 0.5
    }
    
    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при запросе к GPT-4 Turbo")

    # Получаем текст ответа от GPT
    gpt_response = response.json()["choices"][0]["message"]["content"].strip()
    return gpt_response



# Маршрут для добавления резюме
@app.post("/resume/")
def add_resume(resume: ResumeCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Проверяем токен
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Получаем email пользователя из payload
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Обрабатываем описание кандидата с помощью GPT-4 Turbo
    gpt_response = get_link_with_gpt(resume.text)
    print(gpt_response)
    
    # return {"generated_link": gpt_response}
    #пока пропусим эту часть
    resumeJson = get_resume_please(gpt_response)

    if resumeJson is None:
        raise HTTPException(status_code=400, detail="Failed to fetch resume data")

    for resume in resumeJson:
        new_resume = CandidateInDB(
            id=resume["id"],
            user_id=user.id,
            name=resume["name"],
            salary=resume["salary"],
            description=resume["description"],
            experience=resume["experience"],
            expObject=resume["expObject"],
            tags=resume["tags"],
            languages=resume["languages"],
        )
        db.add(new_resume)

    db.commit()

    return {"msg": "Resumes added successfully", "resume_ids": [r["id"] for r in resumeJson]}


@app.post("/create_request/")
def create_request(request: RequestCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Проверяем токен
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Получаем email пользователя из payload
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_request = RequestInDB(
        user_id=user.id,
        title=request.title,
        history="",
        status="open"
    )

    # Добавляем запрос в базу данных
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return {"message": "Request created successfully", "request_id": new_request.id}



@app.post("/chatbot/")
async def chatbot_interaction(
    request: ChatbotRequest,  # Accept the request body as a Pydantic model
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verify access token
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token or unauthorized")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Fetch the specific request (chat) by request_id
    request_obj = db.query(RequestInDB).filter(RequestInDB.id == request.request_id, RequestInDB.user_id == user.id).first()
    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found or not associated with the user")

    # Fetch previous conversation (messages)
    messages = db.query(MessageInDB).filter(MessageInDB.request_id == request.request_id).order_by(MessageInDB.timestamp).all()

    # Prepare chat history for the bot (concatenate previous user and bot messages)
    chat_history = []
    for msg in messages:
        chat_history.append(f"{msg.sender}: {msg.content}")

    # Add user message to chat history
    chat_history.append(f"user: {request.user_message}")
    first_promt = ""
    # Prepare prompt by including entire chat history
    prompt = first_promt + "\n".join(chat_history)

    bot_reply = prompt_to_gpt(prompt)

    user_message = MessageInDB(
        request_id=request.request_id,
        sender="user",
        content=request.user_message,
        timestamp=datetime.utcnow()
    )
    bot_message = MessageInDB(
        request_id=request.request_id,
        sender="bot",
        content=bot_reply,
        timestamp=datetime.utcnow()
    )
    user_message = MessageInDB(
        request_id=request.request_id,
        sender="user",
        content=request.user_message,
        timestamp=datetime.utcnow()
    )
    bot_message = MessageInDB(
        request_id=request.request_id,
        sender="bot",
        content=bot_reply,
        timestamp=datetime.utcnow()
    )

    db.add(user_message)
    db.add(bot_message)
    db.commit()
    if bot_reply == 'Спасибо, вопросов больше нету.':
        summarized_text = summarize_with_gpt(prompt)
        print(summarized_text)
        link = get_link_with_gpt(summarized_text)
        print(link)
        resumeJson = get_resume_please(link)
        print(resumeJson)
        if resumeJson is None:
            raise HTTPException(status_code=400, detail="Failed to fetch resume data")

        for resume in resumeJson:
            new_resume = CandidateInDB(
                user_id=user.id,
                name=resume["name"],
                salary=resume["salary"],
                description=resume["description"],
                experience=resume["experience"],
                expObject=resume["expObject"],
                tags=resume["tags"],
                languages=resume["languages"],
            )
            db.add(new_resume)

        db.commit()
        print('candidates added succesjgoeurjg')
    return {"bot_reply": bot_reply}



@app.get("/messages/{request_id}/")
async def get_messages(
    request_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verify the access token and get the user information
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token or unauthorized")

    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch messages for the specific request (chat)
    messages = db.query(MessageInDB).filter(MessageInDB.request_id == request_id).order_by(MessageInDB.timestamp).all()

    return [{"sender": msg.sender, "content": msg.content, "timestamp": msg.timestamp} for msg in messages]



@app.get("/vacancies/")
def get_vacancies(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    vacancies = db.query(VacancyInDB).filter(VacancyInDB.user_id == user.id).all()
    
    return {"vacancies": [vacancy.__dict__ for vacancy in vacancies]}


@app.delete("/vacancies/{vacancy_id}")
def delete_vacancy(vacancy_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    vacancy = db.query(VacancyInDB).filter(VacancyInDB.id == vacancy_id, VacancyInDB.user_id == user.id).first()

    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    db.delete(vacancy)
    db.commit()

    return {"msg": "Vacancy deleted successfully"}

from vacancie_scraper_hh import get_vacancies

@app.post("/vacancies/parse")
def parse_and_add_vacancies(text: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

   
    vacancies = get_vacancies(text)
    
    if not vacancies:
        raise HTTPException(status_code=404, detail="No vacancies found")


    for vac in vacancies:
        new_vacancy = VacancyInDB(
            title=vac["title"],
            experience=vac["experience"],
            salary=vac["salary"],
            company=vac["company"],
            description=vac["description"],
            link=vac["link"],
            user_id=user.id
        )
        db.add(new_vacancy)

    db.commit()
    
    return {"msg": f"{len(vacancies)} вакансий добавлено"}

def generate_form_with_gpt(description):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }
    data = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты помощник по созданию вопросов. Я хочу чтобы ты создал максимум 3 вопроса. "
                    "Ты должен сделать их в таком формате: ['вопрос1', 'вопрос2', 'вопрос3']. "
                    "НЕ ПИШИ НИЧЕГО ЛИШНЕГО, НИКАКИХ ДОПОЛНИТЕЛЬНЫХ СЛОВ ПРИВЕТСТВИЯ И ТД. "
                    "ТОЛЬКО ВОПРОСЫ В НУЖНОМ ФОРМАТЕ, верни ответ в виде JSON"
                )
            },
            {
                "role": "user",
                "content": f"Создай вопросы на основе следующего описания: {description}"
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.5
    }

    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при запросе к GPT-4 Turbo")

    try:
        gpt_response = response.json()["choices"][0]["message"]["content"].strip()
        questions = json.loads(gpt_response)  # Преобразуем JSON-строку в объект Python
        return questions
    except (KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Ошибка обработки ответа от GPT")


@app.post("/create_form/")
async def create_form(
    prompt: Description, 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    # Проверка доступа пользователя
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Генерация вопросов через GPT
    questions = generate_form_with_gpt(prompt.description)

    # Добавление записей в базу данных
    forms_to_add = []
    for candidate_id in range(1, 21):
        new_form = FormsInDB(
            user_id=user.id,
            candidate_id=str(candidate_id),
            status="Pending",
            questions=json.dumps(questions)  # Храним вопросы в JSON-формате
        )
        forms_to_add.append(new_form)

    # Добавление всех форм за один запрос
    db.add_all(forms_to_add)
    db.commit()  

    # Возвращаем информацию о последней добавленной форме (вы можете вернуть ID самой последней)
    return {"form_id": forms_to_add[-1].id, "questions": questions}

def get_user_questions_and_answers(db: Session, token: str):
    # Проверка и декодирование токена для получения email (sub)
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_email = payload.get("sub")  # Извлекаем email пользователя из токена

    # Находим user_id по email
    user = db.query(UserInDB).filter(UserInDB.email == user_email).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все формы пользователя и связываем их с таблицей кандидатов
    user_forms = (
        db.query(FormsInDB)
        .join(CandidateInDB, FormsInDB.candidate_id == CandidateInDB.id)
        .filter(FormsInDB.user_id == user.id)
        .all()
    )

    # Если формы не найдены
    if not user_forms:
        raise HTTPException(status_code=404, detail="No forms found for the user")

    # Собираем вопросы, ответы и имя кандидата из всех форм
    forms_data = []
    for form in user_forms:
        questions = json.loads(form.questions)  # Десериализуем вопросы из JSON
        answer = form.answer  # Получаем ответ на форму
        candidate_name = form.candidate.name  # Получаем имя кандидата

        forms_data.append({
            "candidate_id": form.candidate_id,
            "candidate_name": candidate_name,  # Добавляем имя кандидата
            "status": form.status,
            "questions": questions,
            "answer": answer
        })

    return {"forms": forms_data}


@app.get("/get_user_questions/")
async def get_user_questions_route(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Получаем вопросы через выделенную функцию
    user_questions = get_user_questions_and_answers(db, token)

    return user_questions


class AnswerUploadRequest(BaseModel):
    candidate_id: int
    answers: List[str]  # Список ответов для вопросов

# Эндпоинт для загрузки ответов кандидатом
@app.post("/upload_answers/{user_id}/")
async def upload_answers(
    user_id: int,
    answer_data: AnswerUploadRequest,
    db: Session = Depends(get_db)  # Получение сессии базы данных
):
    # Находим форму по user_id и candidate_id
    form = db.query(FormsInDB).filter(
        FormsInDB.user_id == user_id,
        FormsInDB.candidate_id == answer_data.candidate_id
    ).first()

    # Проверка на наличие формы
    if form is None:
        raise HTTPException(status_code=404, detail="Form not found for this user and candidate")

    # Обновляем ответы и статус формы
    form.answer = answer_data.answers  # Записываем ответы (список ответов)
    form.status = "complete"  # Обновляем статус на "complete"

    # Сохраняем изменения в базе данных
    db.commit()

    return {"message": "Answers uploaded and status updated successfully"}

client = OpenAI(api_key="")

pc = Pinecone(api_key="")

index = pc.Index("fh")

def extract_important_info(pages):
    prompt = "Extract the following information from the images:\n\n" \
         "Required information: name, education, experience, skills, location, email.\n" \
         "Format the response as JSON with the following structure:\n\n" \
         "{\n  \"name\": \"<Name>\",\n  \"education\": {\n    \"degree\": \"<Degree>\",\n    \"year\": <Year>,\n    \"institution\": \"<Institution>\",\n    \"location\": \"<Location>\",\n    \"field\": \"<Field of study>\"\n  },\n  \"experience\": [\n    {\n      \"job_title\": \"<Job Title>\",\n      \"company\": \"<Company>\",\n      \"duration\": \"<Start Date> — <End Date>\",\n      \"description\": \"<Job Description>\"\n    }\n  ],\n  \"skills\": [\"<Skill1>\", \"<Skill2>\", \"<Skill3>\"],\n  \"location\": \"<Location>\",\n  \"email\": \"<Email Address>\"\n}\n```\n\n" \
         "Ensure all fields are populated based on the information available in the image."


    # Prepare messages with a prompt and all images
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    for page in pages:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract info"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{page}",
                    }
                }
            ]
        })


    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=700,
  response_format={ "type": "json_object" }
      )
    
    return response.choices[0].message.content

def save_to_pinecone(data: dict):
    vector_id = hashlib.md5(data["name"].encode("utf-8")).hexdigest()
    name_text = data.get("name", "")
    education_text = " ".join([
    str(data["education"].get("degree", "")),
    str(data["education"].get("year", "")),
    str(data["education"].get("institution", "")),
    str(data["education"].get("location", "")),
    str(data["education"].get("field", ""))
]) if "education" in data else ""

    
    experience_text = " ".join([
        f"{job.get('job_title', '')} at {job.get('company', '')} ({job.get('duration', '')}): {job.get('description', '')}"
        for job in data.get("experience", [])
    ])
    
    skills_text = " ".join(data.get("skills", []))
    location_text = data.get("location", "")
    email_text = data.get("email", "")
    
    embedding_input = f"{name_text} {education_text} {experience_text} {skills_text} {location_text} {email_text}"
    
    response = client.embeddings.create(
        input=embedding_input,
        model="text-embedding-ada-002"
    ).data[0].embedding

    metadata = {
        "name": data["name"],
        "education": education_text,  # JSON string
        "experience": json.dumps(data.get("experience", []), ensure_ascii=False),  # JSON string
        "skills": data.get("skills", []),  # list of strings
        "location": location_text,
        "email": email_text
    }
    
    index.upsert(vectors=[{"id": vector_id, "values":response, "metadata":metadata}])


@app.post("/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    base64_images = pdf_to_base64_images(file)

    imp = extract_important_info(base64_images)

    data = json.loads(imp)
    
    save_to_pinecone(data)
    
    return {"status": "CV processed and saved successfully", "data": imp}

@app.get("/get-from-db/{name}")
async def get_from_db(name: str):
    response = client.embeddings.create(
        input=name,
        model="text-embedding-ada-002"
    ).data[0].embedding
    print(response)
    result = index.query(vector=[response], top_k=5, include_metadata=True)
    if result.matches:
        return {"data": result.matches[0].metadata}
    else:
        raise HTTPException(status_code=404, detail="CV not found")

def pdf_to_base64_images(pdf_file):
    # Load the PDF
    pdf_document = fitz.open(stream=pdf_file.file.read(), filetype="pdf")
    base64_images = []

    # Iterate over each page
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        pixmap = page.get_pixmap(dpi=300)  # Set DPI for better resolution

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        
        # Save image to a BytesIO buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Encode the image in base64
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_images.append(base64_image)

    pdf_document.close()
    return base64_images