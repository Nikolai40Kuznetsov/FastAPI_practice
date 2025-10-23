from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import csv, os, datetime, uuid
import pandas as pd


app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name = 'static')
app.mount('/templates', StaticFiles(directory='templates'), name='templates')
app.mount('/sources', StaticFiles(directory='sources'), name='sources')
templates = Jinja2Templates(directory = "templates")
USERS = 'users.csv'

# @app.get("/", response_class=HTMLResponse)
# def get_start_page(request: Request):
#     return templates.TemplateResponse("main.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_start_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post('/login')
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):
    users = pd.read_csv(USERS)
    if username in users['user'].values[0]:
        if str(users[users["user"] == username].values[0][1]) == password:
            #session_id = str(uuid.uuid4())
            #session[session_id] = datetime.now()
            response = RedirectResponse(url=f"/main/{username}", status_code=302)
            #response.set_cookie(key='session_id', value=session_id)
            return response
        return templates.TemplateResponse("login.html",
                                          {'request':request,
                                           'error': 'Неверный логин или пароль'})
    
@app.get("/main/admin", response_class=HTMLResponse)
def get_start_page(request:Request):
    return templates.TemplateResponse("main.html", {'request': request})

