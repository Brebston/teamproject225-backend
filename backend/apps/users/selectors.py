from users.models import User


def block_user(user: User):
    user.is_blocked = True
    user.save()

def change_user_role(user: User, new_role: str):
    user.role = new_role
    user.save()
