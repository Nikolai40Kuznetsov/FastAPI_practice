import csv, os
from datetime import timedelta, datetime
import uuid
import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import hashlib


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sources", StaticFiles(directory="sources"), name="sources")
templates = Jinja2Templates(directory="templates")
USERS = "users.csv"
SESSION_TTL = timedelta(1)
sessions = {}
white_urls = ["/", "/login", "/logout"]

def logging(func):                                               
    def wrapper(*args, **kwargs):
        user_func = func
        orig = func(*args, **kwargs)
        user_func_name = str(user_func.__name__)
        user_name = os.getlogin()
        time_act = str(datetime.now().time())
        day_act =  str(datetime.now().date())
        logs = 'logs.csv'
        if os.path.isfile(logs):                                                                                          
            file_df = pd.read_csv(logs)
            data = {'': [len(file_df)], 'User': [user_name], 'Func': [user_func_name], 'Time':[time_act], 'Date':[day_act]}
            df = pd.DataFrame(data)
            df.to_csv('logs.csv',header=False, index=False, mode='a')
        else:                                                                                                         
            data = {'User': [user_name], 'Func': [user_func_name], 'Time':[time_act], 'Date':[day_act]}
            df = pd.DataFrame(data)
            df.to_csv('logs.csv')
        return orig
    return wrapper

@logging
@app.middleware("http")
async def check_session(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path in white_urls:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        return RedirectResponse(url="/")
    
    created_session = sessions[session_id]
    if datetime.now() - created_session > SESSION_TTL:
        del sessions[session_id]
        return RedirectResponse(url="/")

    return await call_next(request)   

@logging
@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@logging
@app.post('/login')
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):
    users = pd.read_csv(USERS)
    if username in users['user'].values[0]:
        if str(users[users["user"] == username].values[0][2]) == password:
            role = users[users["user"] == username].values[0][3]
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f"/main/{username}", status_code=302)
            response.set_cookie(key='session_id', value=session_id)
            return response
    elif username in users['user'].values[1]:
        if str(users[users["user"] == username].values[0][2]) == password:
            role = users[users["user"] == username].values[0][3]
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f"/main/{username}", status_code=302)
            response.set_cookie(key='session_id', value=session_id)
            return response
        return templates.TemplateResponse("login.html",
                                          {'request':request,
                                           'error': 'Неверный пароль'})
    return templates.TemplateResponse("login.html",
                                          {'request':request,
                                           'error': 'Неверный логин'})

@logging
@app.get("/main/admin", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("admin.html", {'request': request})

@logging
@app.get("/main/user", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("main.html", {'request': request})

@app.get("/403", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("403.html", {'request': request})

@app.get("/404", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("404.html", {'request': request})

@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        del sessions[session_id] 
        return templates.TemplateResponse("login.html", {"request": request, "message": "Сессия завершена", "url": "/login"})
    except:
        return RedirectResponse(url=f"/", status_code=302)

@app.exception_handler(404)
def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")
    
