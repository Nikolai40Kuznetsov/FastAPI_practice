from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form, HTTPException, status
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import uuid, time, os, hashlib, unittest, numpy as np
from selenium.webdriver.common.keys import Keys
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from selenium.webdriver.common.by import By
from datetime import timedelta, datetime
from selenium import webdriver
from functools import wraps
import pandas as pd
import ssl
import asyncio

templates = Jinja2Templates(directory='templates')
app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/sources', StaticFiles(directory='sources'), name='sources')

USERS = 'users.csv'
sessions = {}
SESSION_TIME = timedelta(minutes=3)  
MANUAL_LOGOUT_TIME = timedelta(minutes=10) 
white_urls = ['/', '/login', '/logout','/reg','/404', '/403']

def init_admin_user():
    if not os.path.exists(USERS):
        with open(USERS, 'w', encoding='utf-8') as f:
            f.write("user,pass,hash_pass,role\n")        
        admin_password = "admin123"
        admin_hash = hashing_password(admin_password)
        with open(USERS, 'a', encoding='utf-8') as f:
            f.write(f"admin,{admin_password},{admin_hash},admin\n")
        print(f"Создан администратор: admin / {admin_password}")
    else:
        try:
            with open(USERS, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'admin,' not in content:
                    admin_password = "admin123"
                    admin_hash = hashing_password(admin_password)
                    with open(USERS, 'a', encoding='utf-8') as f:
                        f.write(f"admin,{admin_password},{admin_hash},admin\n")
                    print(f"Добавлен администратор: admin / {admin_password}")
        except Exception as e:
            print(f"Ошибка при проверке файла пользователей: {e}")

def logger():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            work_time = round(end_time - start_time, 4)
            if os.path.exists('log.csv'):
                df = pd.read_csv('log.csv')
            else:
                df = pd.DataFrame(columns=["func_name", "work_time", "date_time"])

            data = {
                "func_name": func.__name__,
                "work_time": work_time,
                "date_time": pd.Timestamp.now()
            }
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            df.to_csv("log.csv", index=False, encoding="utf-8")
            return result
        return wrapper
    return decorator

def hashing_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_info(request: Request):
    username = request.cookies.get('username')
    role = request.cookies.get('role')
    return username, role

def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            username, role = get_user_info(request)
            if role != required_role:
                return RedirectResponse(url='/403')
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.middleware('http')
async def check_session(request: Request, call_next):
    if request.url.path in white_urls or request.url.path.startswith('/static') or request.url.path.startswith('/sources'):
        return await call_next(request)    
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        return RedirectResponse(url='/login')    
    session_data = sessions[session_id]
    if datetime.now() - session_data['last_activity'] > SESSION_TIME:
        del sessions[session_id]
        return RedirectResponse(url='/login')
    sessions[session_id]['last_activity'] = datetime.now()
    if datetime.now() - session_data['login_time'] > MANUAL_LOGOUT_TIME:
        response = await call_next(request)
        if hasattr(response, 'headers'):
            response.headers['X-Show-Logout-Modal'] = 'true'
        return response
    return await call_next(request)

@app.get("/", response_class=HTMLResponse)
@logger()
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
@logger()
async def get_login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@app.post('/login')
@logger()
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not os.path.exists(USERS):
        init_admin_user()    
    try:
        users = pd.read_csv(USERS)
        print(f"Users in database: {users['user'].tolist()}")        
        user_exists = users[users['user'] == username]
        hash_password = hashing_password(password)        
        if not user_exists.empty:
            stored_hash = user_exists.iloc[0]['hash_pass']
            print(f"Login attempt: {username}")
            print(f"Stored hash: {stored_hash}")
            print(f"Provided hash: {hash_password}")
            print(f"Match: {stored_hash == hash_password}")            
            if user_exists.iloc[0]['hash_pass'] == hash_password:
                session_id = str(uuid.uuid4())
                sessions[session_id] = {
                    'username': username,
                    'role': user_exists.iloc[0]['role'],
                    'login_time': datetime.now(),
                    'last_activity': datetime.now()
                }        
                response = RedirectResponse(url=f'/main/{username}', status_code=303)
                response.set_cookie(key='session_id', value=session_id)
                response.set_cookie(key='username', value=username)
                response.set_cookie(key='role', value=user_exists.iloc[0]['role'])
                return response
    except Exception as e:
        print(f"Error during login: {e}")
        init_admin_user()
    
    return templates.TemplateResponse(
        'login.html',
        {'request': request, 'error': 'Неверный логин или пароль'}
    )

@app.get("/logout", response_class=HTMLResponse)
@logger()
async def logout(request: Request):
    session_id = request.cookies.get('session_id')
    if session_id in sessions:
        del sessions[session_id]    
    response = templates.TemplateResponse('login.html', {
        'request': request, 
        'message': 'Вы были выброшены из сессии'
    })
    response.delete_cookie('session_id')
    response.delete_cookie('username')
    response.delete_cookie('role')
    return response

@app.get('/main/{username}', response_class=HTMLResponse)
@logger()
async def get_home_page(request: Request, username: str):
    current_username, role = get_user_info(request)
    if current_username != username:
        return RedirectResponse(url='/403')    
    show_logout_modal = False
    session_id = request.cookies.get('session_id')
    if session_id in sessions:
        session_data = sessions[session_id]
        if datetime.now() - session_data['login_time'] > MANUAL_LOGOUT_TIME:
            show_logout_modal = True    
    return templates.TemplateResponse('admin.html', {
        'request': request, 
        'username': username,
        'role': role,
        'show_logout_modal': show_logout_modal
    })

@app.get('/admin/create-user', response_class=HTMLResponse)
@logger()
@require_role('admin')
async def get_create_user_page(request: Request):
    username, role = get_user_info(request)
    return templates.TemplateResponse('create_user.html', {
        'request': request,
        'username': username,
        'role': role
    })

@app.post('/admin/create-user')
@logger()
@require_role('admin')
async def create_user(
    request: Request, 
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    role: str = Form(...)
):
    if not os.path.exists(USERS):
        init_admin_user()
    
    try:
        users = pd.read_csv(USERS)
    except Exception as e:
        print(f"Error reading users: {e}")
        return templates.TemplateResponse('create_user.html', {
            'request': request,
            'error': 'Ошибка базы данных',
            'username': request.cookies.get('username'),
            'role': request.cookies.get('role')
        })
    
    if password != password_confirm: 
        return templates.TemplateResponse('create_user.html', {
            'request': request,
            'error': 'Пароли не совпадают',
            'username': request.cookies.get('username'),
            'role': request.cookies.get('role')
        })
    elif username in users['user'].values:
        return templates.TemplateResponse('create_user.html', {
            'request': request,
            'error': 'Имя пользователя занято',
            'username': request.cookies.get('username'),
            'role': request.cookies.get('role')
        })
    else:
        hash_pass = hashing_password(password)
        new_user = f"{username},{password},{hash_pass},{role}\n"
        with open(USERS, 'a', encoding='utf-8') as f:
            f.write(new_user)        
        return templates.TemplateResponse('create_user.html', {
            'request': request,
            'success': f'Пользователь {username} успешно создан',
            'username': request.cookies.get('username'),
            'role': request.cookies.get('role')
        })

@app.get('/reg', response_class=HTMLResponse)
@logger()
async def get_registration_page(request: Request):
    return templates.TemplateResponse("reg.html", {"request": request})

@app.post("/reg")
@logger()
async def registration(
    request: Request, 
    username: str = Form(...),
    password: str = Form(...), 
    password_confirm: str = Form(...)
):
    if not os.path.exists(USERS):
        init_admin_user()
    
    try:
        users = pd.read_csv(USERS)
    except Exception as e:
        print(f"Error reading users: {e}")
        return templates.TemplateResponse('reg.html', {
            'request': request, 
            'error': 'Ошибка базы данных'
        })
    
    if password != password_confirm: 
        return templates.TemplateResponse('reg.html', {
            'request': request, 
            'error': 'Пароли не совпадают'
        })
    elif username in users['user'].values:
        return templates.TemplateResponse('reg.html', {
            'request': request, 
            'error': 'Имя пользователя занято'
        })
    else:
        hash_pass = hashing_password(password)
        user_role = "user"
        new_user = f"{username},{password},{hash_pass},{user_role}\n"
        with open(USERS, 'a', encoding='utf-8') as f:
            f.write(new_user)        
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'username': username,
            'role': user_role,
            'login_time': datetime.now(),
            'last_activity': datetime.now()
        }        
        response = RedirectResponse(url=f'/main/{username}', status_code=303)
        response.set_cookie(key='session_id', value=session_id)
        response.set_cookie(key='username', value=username)
        response.set_cookie(key='role', value=user_role)
        return response

@app.get("/404", response_class=HTMLResponse)
@logger()
async def error_page(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})

@app.get("/403", response_class=HTMLResponse)
@logger()
async def forbidden_page(request: Request):
    return templates.TemplateResponse("403.html", {"request": request})

@app.exception_handler(404)
@logger()
async def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")

@app.exception_handler(403)
@logger()
async def forbidden_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)

class WebsiteTests(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")  
        chrome_options.add_argument("--allow-insecure-localhost")   
        self.driver = webdriver.Chrome(options=chrome_options)
        self.base_url = "https://localhost:8000"  
        self.driver.implicitly_wait(10)

    def tearDown(self):
        self.driver.quit()

    def test_login_page(self):
        self.driver.get(f"{self.base_url}/login")
        self.assertIn("Login", self.driver.title)
        
    def test_registration_page(self):
        self.driver.get(f"{self.base_url}/reg")
        self.assertIn("Registration", self.driver.title)
        
    def test_admin_login(self):
        self.driver.get(f"{self.base_url}/login")
        username_field = self.driver.find_element(By.NAME, "username")
        password_field = self.driver.find_element(By.NAME, "password")        
        username_field.send_keys("admin")
        password_field.send_keys("admin123")
        password_field.send_keys(Keys.RETURN)
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/main/admin")
        )
        self.assertIn("admin", self.driver.current_url)

def run_tests():
    print("Starting automated tests with HTTPS...")
    unittest.main(argv=[''], verbosity=2, exit=False)

@app.on_event("startup")
async def startup_event():
    print("Initializing admin user...")
    init_admin_user()
    if os.path.exists(USERS):
        with open(USERS, 'r', encoding='utf-8') as f:
            content = f.read()
            print("Current users.csv content:")
            print(content)
    
    print("Admin credentials: admin / admin123")
    run_tests()

if __name__ == "__main__":
    import uvicorn    
    print("Starting server on https://localhost:8000")
    print("Admin credentials: admin / admin123")
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        print("SSL certificates not found! Generating...")
        os.system('openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=localhost"')
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_certfile="cert.pem", 
        ssl_keyfile="key.pem"
    )