from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from datetime import timezone, timedelta

from app.db import (
    get_status,
    get_all_users,
    add_user,
    delete_user,
    SessionLocal,
    get_user_by_id,
    engine,
    Base
)
from app.models import RoleEnum, User, ActionLog
from app.config import ADMIN_API_KEY


# Часовой пояс Москва
MSK = timezone(timedelta(hours=3))


def create_tables():
    Base.metadata.create_all(bind=engine)


app = FastAPI()
create_tables()

app.mount("/static", StaticFiles(directory="app/admin/static"), name="static")
templates = Jinja2Templates(directory="app/admin/templates")


def require_admin(request: Request):
    key = request.cookies.get("admin_key")
    return key == ADMIN_API_KEY


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, key: str = Form(...)):
    if key == ADMIN_API_KEY:
        resp = RedirectResponse("/admin", status_code=302)
        resp.set_cookie(
            "admin_key",
            ADMIN_API_KEY,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=3600
        )
        return resp

    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный ключ"})


@app.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login")

    st = get_status()
    status_value = st.status if st else "unknown"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "status": status_value}
    )


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login")

    users = get_all_users()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users}
    )


@app.post("/admin/users/add")
def admin_add_user(
        request: Request,
        name: str = Form(...),
        tg_id: str = Form(...),
        role: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse("/login")

    try:
        tg_int = int(tg_id)
    except ValueError:
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "users": get_all_users(),
                "error": "Telegram ID должен быть числом"
            }
        )

    try:
        role_enum = RoleEnum(role)
    except ValueError:
        role_enum = RoleEnum.guest

    add_user(
        tg_id=tg_int,
        name=name,
        role=role_enum
    )

    return RedirectResponse("/admin/users", status_code=302)


@app.get("/admin/users/delete/{user_id}")
def admin_delete_user(request: Request, user_id: int):
    if not require_admin(request):
        return RedirectResponse("/login")

    delete_user(user_id)
    return RedirectResponse("/admin/users", status_code=302)


@app.get("/admin/users/edit/{user_id}", response_class=HTMLResponse)
def edit_user_page(request: Request, user_id: int):
    if not require_admin(request):
        return RedirectResponse("/login")

    user = get_user_by_id(user_id)
    return templates.TemplateResponse(
        "edit_user.html",
        {"request": request, "user": user}
    )


@app.post("/admin/users/edit/{user_id}")
def edit_user_action(
        request: Request,
        user_id: int,
        name: str = Form(...),
        tg_id: str = Form(...),
        role: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse("/login")

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()

    user.name = name
    user.telegram_id = tg_id

    try:
        user.role = RoleEnum(role)
    except ValueError:
        user.role = RoleEnum.guest

    db.commit()
    db.close()

    return RedirectResponse("/admin/users", status_code=302)


@app.get("/admin/logs", response_class=HTMLResponse)
def admin_logs(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login")

    db = SessionLocal()
    logs = db.query(ActionLog).order_by(ActionLog.id.desc()).all()

    formatted_logs = []

    for log in logs:
        # ИЩЕМ ПОЛЬЗОВАТЕЛЯ ПО telegram_id
        user = db.query(User).filter(User.telegram_id == str(log.actor)).first()

        if user:
            name = user.name
            tg_id = user.telegram_id
        else:
            name = "Не найден"
            tg_id = log.actor

        # Преобразование действия
        if log.action == "set_on":
            action_label = "Включено"
        elif log.action == "set_off":
            action_label = "Выключено"
        else:
            action_label = log.action

        # Преобразование деталей
        if log.details and "old_status=" in log.details:
            raw = log.details.split("=")[1]
            status_human = "Включено" if raw == "on" else "Выключено"
            details_label = f"Прошлый статус: {status_human}"
        else:
            details_label = log.details

        # Дата МСК
        timestamp = log.timestamp.astimezone(MSK).strftime("%d.%m.%Y %H:%M:%S")

        formatted_logs.append({
            "id": log.id,
            "name": name,
            "tg_id": tg_id,
            "action": action_label,
            "details": details_label,
            "timestamp": timestamp
        })

    db.close()

    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "logs": formatted_logs}
    )


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/login")
