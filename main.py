from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form, HTTPException
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

templates = Jinja2Templates(directory='templates')
app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/sourses', StaticFiles(directory='sourses'), name='sourses')

USERS = 'users.csv'
sessions = {}
SESSION_TIME = timedelta(minutes=10)
white_urls = ['/', '/login', '/logout','/reg','/404']

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
    users = pd.read_csv(USERS)
    print(users)
    if ((users['user'] == username) & (users['pass'] == password)).any():
        session_id = str(uuid.uuid4())
        sessions[session_id] = datetime.now()
        response = RedirectResponse(url=f'/main/{username}', status_code=303)
        response.set_cookie(key='session_id', value=session_id)
        return response
    return templates.TemplateResponse(
        'login.html',
        {'request': request, 'error': 'Неверный логин или пароль'}
    )

@app.get("/logout", response_class=HTMLResponse)
@logger()
async def logout(request : Request):
    session_id = request.cookies.get('session_id')
    print(session_id)
    del sessions[session_id]
    return templates.TemplateResponse('login.html', {'request' : request, 
                                    'message' : 'Вы были выброшены из сессии'})

@app.get('/main/{username}', response_class=HTMLResponse)
@logger()
async def get_home_page(request: Request, username: str):
    users = pd.read_csv(USERS)
    return templates.TemplateResponse('admin.html', {'request': request, 'username': username})

@app.get('/reg', response_class=HTMLResponse)
@logger()
async def get_registration_page(request : Request):
    return templates.TemplateResponse("reg.html", {"request": request})

@app.post("/reg")
@logger()
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

@logger()
async def eror_page(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})

@app.exception_handler(404)
@logger()
async def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")

class TestStringMethods(unittest.TestCase):

    def test_admin_login(self):
        driver = webdriver.Chrome()
        driver.get("https://127.0.0.1")

        time.sleep(5)

        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys("admin")
        passwd_input.send_keys("admin")

        submit_btn.click()
        self.assertEqual(driver.find_element(By.XPATH, value='/html/body/div/h1').get_attribute("textContent"), "Добро пожаловать, admin!")
        driver.quit()

    def test_admin_registration_and_user_login(self):
        TESTING_NICKNAME = "testSuiteUser"
        TESTING_PWD = "1234"
        driver = webdriver.Chrome()
        driver.get("https://127.0.0.1")

        time.sleep(5)

        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys("admin")
        passwd_input.send_keys("admin")

        submit_btn.click()


        time.sleep(5)
        new_user_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        new_pwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        new_user_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        new_user_input.clear()
        new_pwd_input.clear()

        new_user_input.send_keys(TESTING_NICKNAME)
        new_pwd_input.send_keys(TESTING_PWD)
        new_user_btn.click()

        leave_link = driver.find_element(By.XPATH, value='/html/body/div/a')
        leave_link.click()


        time.sleep(5)
        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys(TESTING_NICKNAME)
        passwd_input.send_keys(TESTING_PWD)
        submit_btn.click()
        self.assertEqual(driver.find_element(By.XPATH, value='/html/body/div/h1').get_attribute("textContent"), f"Добро пожаловать, {TESTING_NICKNAME}!")
        driver.quit()

    def alert_session_continue_test(self):
        driver = webdriver.Chrome()
        driver.get("https://127.0.0.1")

        time.sleep(5)

        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys("admin")
        passwd_input.send_keys("admin")

        submit_btn.click()
        try:
            WebDriverWait(driver, 180).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            
            print("Alert text:", alert.text)
            alert.accept()
            
        except NoAlertPresentException:
            print("No alert was present.")
        self.assertEqual(alert.text, "Сессия продлена")
        driver.quit()
        

    def alert_session_break_test(self):
        driver = webdriver.Chrome()
        driver.get("https://127.0.0.1")

        time.sleep(5)

        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys("admin")
        passwd_input.send_keys("admin")

        submit_btn.click()
        try:
            WebDriverWait(driver, 180).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            
            print("Alert text:", alert.text)
            alert.dismiss()
            
        except NoAlertPresentException:
            print("No alert was present.")
        self.assertEqual(driver.find_element(By.XPATH, value='/html/body/div/form/button').get_attribute("textContent"), "Войти")
        driver.quit()

    def test_404(self):
        driver404 = webdriver.Chrome()
        driver404.get("https://127.0.0.1/fantastic/site/that/should/be/never/existed")

        time.sleep(5)

        header = driver404.find_element(By.XPATH, value='/html/body/h1')
        self.assertEqual(header.get_attribute("textContent"), "Page not found (404 ERROR)")
        driver404.quit()

    def test_403(self):
        driver403 = webdriver.Chrome()
        driver403.get("https://127.0.0.1/admin")

        time.sleep(5)

        header = driver403.find_element(By.XPATH, value='/html/body/h1')
        self.assertEqual(header.get_attribute("textContent"), "FORBIDDEN (403 ERROR)") 
        driver403.quit()

    def incorrect_pwd(self):
        driver = webdriver.Chrome()
        driver.get("https://127.0.0.1")

        login_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[1]')
        passwd_input = driver.find_element(By.XPATH, value='/html/body/div/form/input[2]')
        submit_btn = driver.find_element(By.XPATH, value='/html/body/div/form/button')

        login_input.clear()
        passwd_input.clear()

        login_input.send_keys("admin")
        passwd_input.send_keys("123")

        submit_btn.click()
        try:
            error_msg = driver.find_element(By.XPATH, value='/html/body/div/p[1]')
            self.assertEqual(error_msg.get_attribute("textContent"), "Неверный логин или пароль") 
        except NoSuchElementException:
            print("Element does not exist.")
        driver.quit()

if __name__ == '__main__':
    unittest.main()