# Подключение всех статических файлов, шаблонов,
# инициализация веб-приложения, описание глобальных переменных
from datetime import timedelta
import hashlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
USERS = "users.csv"
SESSION_TTL = timedelta(10)
sessions = {}
white_urls = ["/", "/login", "/logout"]
hasher = hashlib.sha256()
