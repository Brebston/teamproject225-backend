def get_user_full_name(user):
    profile = getattr(user, "profile", None)
    if profile:
        full_name = f"{profile.first_name} {profile.last_name}".strip()
        if full_name:
            return full_name

    specialist = getattr(user, "specialist_profile", None)
    if specialist:
        full_name = f"{specialist.first_name} {specialist.last_name}".strip()
        if full_name:
            return full_name

    return user.email


def get_user_avatar(user):
    profile = getattr(user, "profile", None)
    if profile and profile.avatar:
        return profile.avatar.url

    specialist = getattr(user, "specialist_profile", None)
    if specialist and specialist.avatar:
        return specialist.avatar.url

    return None
