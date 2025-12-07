from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, SiteStatus, ActionLog, RoleEnum
from app.config import DB_URL

engine = create_engine(DB_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)


def init_db():
    Base.metadata.create_all(bind=engine)
    ses = SessionLocal()
    try:
        if ses.query(SiteStatus).count() == 0:
            ses.add(SiteStatus(id=1, status="off"))
            ses.commit()
    finally:
        ses.close()


def add_user(tg_id: int, name: str, role: RoleEnum):
    ses = SessionLocal()
    try:
        user = User(
            telegram_id=str(tg_id),
            name=name,
            role=role
        )
        ses.add(user)
        ses.commit()
        ses.refresh(user)
        return user
    finally:
        ses.close()


def get_user_by_tg_id(tg_id: int):
    ses = SessionLocal()
    try:
        return ses.query(User).filter(User.telegram_id == str(tg_id)).first()
    finally:
        ses.close()


def get_user_by_id(uid: int):
    ses = SessionLocal()
    try:
        return ses.query(User).filter(User.id == uid).first()
    finally:
        ses.close()


def delete_user(user_id: int):
    ses = SessionLocal()
    try:
        u = ses.query(User).filter_by(id=user_id).first()
        if u:
            ses.delete(u)
            ses.commit()
    finally:
        ses.close()


def get_all_users():
    ses = SessionLocal()
    try:
        return ses.query(User).all()
    finally:
        ses.close()


def get_all_receivers():
    ses = SessionLocal()
    try:
        users = ses.query(User).filter(
            User.role.in_([RoleEnum.admin, RoleEnum.notifier])
        ).all()

        res = []
        for u in users:
            if u.telegram_id and u.telegram_id.isdigit():
                res.append(int(u.telegram_id))
        return res
    finally:
        ses.close()


def get_status():
    ses = SessionLocal()
    try:
        return ses.get(SiteStatus, 1)
    finally:
        ses.close()


def set_status(new_status: str, actor_id: int | str):
    ses = SessionLocal()
    try:
        st = ses.get(SiteStatus, 1)

        if not st:
            st = SiteStatus(id=1, status=new_status, updated_by=str(actor_id))
            ses.add(st)
        else:
            old = st.status
            st.status = new_status
            st.updated_by = str(actor_id)

        ses.add(ActionLog(
            actor=str(actor_id),
            action=f"set_{new_status}",
            details=f"old_status={old if 'old' in locals() else 'unknown'}"
        ))

        ses.commit()
        ses.refresh(st)
        return st
    finally:
        ses.close()
