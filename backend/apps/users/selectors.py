from users.models import User


def get_active_users():
    return User.objects.filter(is_blocked=False)


def get_specialists():
    return User.objects.filter(role=User.Roles.SPECIALIST)