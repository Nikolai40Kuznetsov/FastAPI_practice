from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import timedelta, datetime
import uuid
import time
from datetime import datetime
import pandas as pd
import os
import hashlib
from functools import wraps

templates = Jinja2Templates(directory='templates')
app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

USERS = 'users.csv'
sessions = {}
SESSION_TIME = timedelta(minutes=10)
white_urls = ['/', '/login', '/logout','/reg','/404']

# def logger():
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             start_time = time.time()
#             result = await func(*args, **kwargs)
#             end_time = time.time()
#             work_time = round(end_time - start_time, 4)
#             if os.path.exists('log.csv'):
#                 df = pd.read_csv('log.csv')
#             else:
#                 df = pd.DataFrame(columns=["func_name", "work_time", "date_time"])

#             data = {
#                 "func_name": func.__name__,
#                 "work_time": work_time,
#                 "date_time": pd.Timestamp.now()
#             }
#             df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
#             df.to_csv("log.csv", index=False, encoding="utf-8")
#             return result
#         return wrapper
#     return decorator

def hashing_password(password : str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()



@app.middleware('http')
async def check_session(request: Request, call_next):
    if request.url.path in white_urls or request.url.path.startswith('/static'):
        return await call_next(request)
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        return RedirectResponse(url='/login')
    if datetime.now() - sessions[session_id] > SESSION_TIME:
        del sessions[session_id]
        return RedirectResponse(url='/login')
    return await call_next(request)

@app.get("/", response_class=HTMLResponse)
# @logger()
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
# @logger()
async def get_login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@app.post('/login')
# @logger()
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = pd.read_csv(USERS)
    print(users)
    if ((users['user'] == username) & (users['pass'] == password)).any():
        session_id = str(uuid.uuid4())
        sessions[session_id] = datetime.now()
        response = RedirectResponse(url=f'/home/{username}', status_code=303)
        response.set_cookie(key='session_id', value=session_id)
        return response
    return templates.TemplateResponse(
        'login.html',
        {'request': request, 'error': 'Неверный логин или пароль'}
    )

@app.get("/logout", response_class=HTMLResponse)
# @logger()
async def logout(request : Request):
    session_id = request.cookies.get('session_id')
    print(session_id)
    del sessions[session_id]
    return templates.TemplateResponse('login.html', {'request' : request, 
                                    'message' : 'Вы были выброшены из сессии'})

@app.get('/home/{username}', response_class=HTMLResponse)
# @logger()
async def get_home_page(request: Request, username: str):
    users = pd.read_csv(USERS)
    return templates.TemplateResponse('main.html', {'request': request, 'username': username})

@app.get('/reg', response_class=HTMLResponse)
# @logger()
async def get_registration_page(request : Request):
    return templates.TemplateResponse("reg.html", {"request": request})

@app.post("/reg")
# @logger()
async def registration(request: Request, username: str = Form(...),
                        password: str = Form(...), 
                        password_confirm: str = Form(...)):
    users = pd.read_csv(USERS)
    if password != password_confirm: 
        return templates.TemplateResponse('reg.html', 
                                           {'request' : request, 
                                           'error' : 'Пароли не совпадают'})
    elif username in users['user']:
        return templates.TemplateResponse('reg.html', 
                                           {'request' : request, 
                                           'error' : 'Имя пользователя занято'})
    else:
        hash_pass = hashing_password(password)

        if username == 'admin':
            new_user = pd.DataFrame([{"user": username,
                                       "pass": password,
                                       "hash_pass": hash_pass,
                                       "role": "admin"}])
        else: 
            new_user = pd.DataFrame([{"user": username,
                                       "pass": password,
                                       "hash_pass": hash_pass,
                                       "role": "user"}])
        users = pd.concat([users, new_user], ignore_index=True)
        users.to_csv(USERS, index=False, encoding="utf-8")
        session_id = str(uuid.uuid4())
        sessions[session_id] = datetime.now()
        response = RedirectResponse(url=f'/home/{username}', status_code=303)
        response.set_cookie(key='session_id', value=session_id)
        return response

@app.get("/404", response_class=HTMLResponse)

# @logger()
async def eror_page(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})

@app.exception_handler(404)
# @logger()
async def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")