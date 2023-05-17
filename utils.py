from django.http import HttpResponse
from django.template import loader
import pdfkit

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


def render_attached_pdf(relative_template_path, context, file_name, css=[]):
    html = loader.render_to_string(relative_template_path, context)

    output = pdfkit.from_string(
        html,
        output_path=False,
        css= css if len(css) > 0 else []
    )
    response = HttpResponse(output)
    response["Content-Type"] = "application/pdf"
    response["Content-Disposition"] = "attachment; filename=%s" %(file_name)
    return response