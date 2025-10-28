from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import csv, os, uuid, hashlib
import pandas as pd
from datetime import datetime, timedelta


app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name = 'static')
app.mount('/templates', StaticFiles(directory='templates'), name='templates')
app.mount('/sources', StaticFiles(directory='sources'), name='sources')
templates = Jinja2Templates(directory = "templates")
USERS = 'users.csv'
SESSION_TTL = timedelta(minutes=1)
sessions = {}
white_urls = ["/", "/login", "/logout"]

@app.middleware("http")
async def check_session(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path in ["/", "/login", "/logout"]:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/login")

    created_at = sessions[session_id]
    if datetime.now() - created_at > SESSION_TTL:
        del sessions[session_id]
        return templates.TemplateResponse("login.html", {"request" : request, "message" : "Сессия завершена по истечении времени"}) # RedirectResponse(url="/login")

    return await call_next(request)
    


@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        del sessions[session_id]
        return templates.TemplateResponse("login.html", {"request" : request, "message" : "Сессия завершена из-за действий пользователя"})
    except:
        return templates.TemplateResponse("login.html", {"request": request})

@app.post('/login')
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):
    users = pd.read_csv(USERS)
    if username in users['user'].values[0]:
        if str(users[users["user"] == username].values[0][2]) == password:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f"/main/{username}", status_code=302)
            response.set_cookie(key='session_id', value=session_id)
            return response
    elif username in users['user'].values[1]:
        if str(users[users["user"] == username].values[0][2]) == password:
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
    
@app.get("/main/admin", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("admin.html", {'request': request})

@app.get("/main/user", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("main.html", {'request': request})

@app.get("/403", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("403.html", {'request': request})

@app.get("/404", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("404.html", {'request': request})

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    response = RedirectResponse(url="/")
    response.delete_cookie("session_id")
    return response

@app.exception_handler(404)
def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")
    
@app.exception_handler(403)
def not_allowed_page(request: Request, exc):
    return RedirectResponse(url="/403")