from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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