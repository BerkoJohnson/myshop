def get_uuid(id):
    import uuid
    try:
        uid = uuid.UUID(id)
    except ValueError:
        return None
    else:
        return uid


def is_admin(user):
    return user.user_type == "ADMIN"


def is_sale_person(user):
    return user.user_type == "SALEPERSON"


def image_path(path, instance, filename):
    return f"{path}/{instance.pk}/{filename}"
