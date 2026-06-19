from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import db_manager


def ensure_default_admin_user() -> None:
    db_manager.init_db()
    user_row = db_manager.get_user_by_username(Config.ADMIN_USERNAME)
    password_hash = generate_password_hash(Config.ADMIN_PASSWORD)
    if user_row is None:
        db_manager.create_user(Config.ADMIN_USERNAME, password_hash, role='admin')
    else:
        db_manager.update_user_password(Config.ADMIN_USERNAME, password_hash)


def authenticate_user(username: str, password: str) -> bool:
    db_manager.init_db()
    user_row = db_manager.get_user_by_username(username)
    if user_row is not None:
        return check_password_hash(user_row['password_hash'], password)
    return False
