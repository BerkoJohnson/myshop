from core.models import Product, Order, OrderItem
from django.shortcuts import render
from django.http import HttpResponse

from django.contrib.auth.decorators import login_required, user_passes_test
from utils import is_sale_person


@login_required
@user_passes_test(is_sale_person)
def index(request):
    return render(
        request,
        "sales/index.html"
    )
