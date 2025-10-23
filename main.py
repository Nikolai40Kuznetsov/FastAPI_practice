from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import datetime
import uuid

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sources", StaticFiles(directory="sources"), name="sources")
templates = Jinja2Templates(directory="templates")
USERS = "users.csv"
# SESSION_TTL = timedelta(10)
sessions = {}
white_urls = ["/", "/login", "/logout"]

@app.get("/", response_class=HTMLResponse)
def get_start_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/main", response_class=HTMLResponse)
def get_start_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = pd.read_csv("users.csv")
    if username in users['user'].values[0]:
        if str(users[users["user"] == username].values[0][1]) == password:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()