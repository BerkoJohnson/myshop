from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from .models import Product, Order, OrderItem
from utils import is_admin
import io
from .tasks import import_products_task, remove_products_task
from celery.result import AsyncResult
from celery_progress.backend import Progress
import csv
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .forms import ProductCreationForm


@login_required
@user_passes_test(is_admin)
def index(request):
    return render(request, "core/index.html")


@login_required
@user_passes_test(is_admin)
def products_home(request):
    products = Product.objects.all()
    context = {
        "products": products,
    }
    return render(request, "core/products/products.html", context)


@login_required
@user_passes_test(is_admin)
def load_products(request):
    limit = request.GET.get("l")
    page = request.GET.get("p")
    search_term = request.GET.get("s") if request.GET.get("s") is not None else ""

    if limit is not None:
        limit = int(limit)

    products = Product.objects.all().order_by("-created")
    if search_term != "":
        products = products.filter(Q(name__icontains=search_term)).order_by("-created")

    paginator = Paginator(object_list=products, per_page=limit)

    if page is None:
        page = 1

    page_obj = paginator.get_page(page)

    starting_number = 1
    stopping_number = limit

    if page_obj.has_previous():
        starting_number = page_obj.previous_page_number() * limit
        stopping_number = starting_number + limit

    pages = [
        {"number": page, "allow": type(page) == int}
        for page in list(page_obj.paginator.get_elided_page_range())
    ]

    context = {
        "page_obj": page_obj,
        "number_of_products": len(products),
        "starting_number": starting_number,
        "stopping_number": stopping_number,
        "limit": limit,
        "search_term": search_term,
        "pages": pages,
    }
    return render(request, "core/partials/table_search.html", context)


@login_required
@user_passes_test(is_admin)
def update_product_stock(request, product_id):
    product = Product.objects.get(pk=product_id)
    if request.method == "POST":
        stock = request.POST.get("stock")

        product.stock = stock
        product.save()
        context = {"product": product}
        return render(request, "core/partials/product_table_row.html", context)
    return HttpResponse(b"Not Allowed")


@login_required
@user_passes_test(is_admin)
def import_products(request):
    context = {}
    return render(
        request,
        "core/products/import_products.html",
        context,
    )


def do_import_products(request):
    if request.method == "POST":
        if bool(request.FILES.get("file")):
            file = io.TextIOWrapper(request.FILES.get("file"))
            csv_reader = csv.DictReader(file)
            rows = [row for row in csv_reader if row.get("PRODUCT") != ""]

            import_task = import_products_task.delay(rows)
            task_id = import_task.task_id
            progress = Progress(AsyncResult(task_id))
            info = progress.get_info()
            context = {
                "task_id": task_id,
                "info": info,
            }
            return render(
                request, "core/products/import_products_progress.html", context
            )
        else:
            context = {"error": "No file submitted"}

            return render(
                request,
                "core/products/import_products.html",
                context,
            )


@login_required
@user_passes_test(is_admin)
def track_import_progress(request, task_id):
    progress = Progress(AsyncResult(task_id))
    info = progress.get_info()

    context = {
        "task_id": task_id,
        "info": info,
    }
    response = render(request, "core/products/import_products_progress.html", context)
    if info["complete"]:
        response["HX-TRIGGER"] = "reload_products_table"
    return response


@login_required
@user_passes_test(is_admin)
def remove_all_products(request):
    context = {}
    return render(request, "core/products/remove_products_question.html", context)


@login_required
@user_passes_test(is_admin)
def track_remove_product_progress(request, task_id):
    progress = Progress(AsyncResult(task_id))
    info = progress.get_info()

    context = {
        "task_id": task_id,
        "info": info,
    }
    response = render(request, "core/products/remove_products_progress.html", context)
    if info["complete"]:
        response["HX-TRIGGER"] = "reload_products_table"
    return response


@login_required
@user_passes_test(is_admin)
def get_product_action_buttons(request):
    return render(request, "core/partials/product_action_buttons.html")


@login_required
@user_passes_test(is_admin)
def remove_all_products_question(request):
    context = {"ids": []}
    if request.method == "POST":
        context["ids"] = request.POST.getlist("ids")
    return render(request, "core/products/remove_all_products_question.html", context)


@login_required
@user_passes_test(is_admin)
def do_remove_products(request):
    ids = []
    if request.method == "POST":
        if request.POST.getlist("ids") is not None:
            ids = request.POST.getlist("ids")

    remove_task = remove_products_task.delay(ids)
    task_id = remove_task.task_id
    progress = Progress(AsyncResult(task_id))
    info = progress.get_info()

    context = {
        "task_id": task_id,
        "info": info,
        "selected_removal": len(ids) > 0,
        "count": len(ids) if len(ids) > 0 else Product.objects.count(),
    }
    return render(request, "core/products/remove_products_progress.html", context)


@login_required
@user_passes_test(is_admin)
def add_product(request):
    form_title = "Enter new product details below"
    form = ProductCreationForm()
    if request.method == "POST":
        form = ProductCreationForm(request.POST)

        if form.is_valid():
            try:
                product = form.save(commit=False)

                if int(form.cleaned_data["cost"]) > 0:
                    product.profit_rate = abs(int(form.cleaned_data["cost"])) / abs(
                        int(form.cleaned_data["price"])
                    )
                else:
                    product.profit_rate = 0
                product.save()
            except Exception as e:
                print(e)
                context = {
                    "type": "danger",
                    "message": "New product could not be saved. Try again later.",
                }
                return render(request, "core/products/response.html", context)
            else:
                context = {
                    "type": "success",
                    "message": "New product successfully saved.",
                }
                response = render(request, "core/products/response.html", context)
                response["HX-TRIGGER"] = "reload_products_table"
                return response

    context = {"form": form, "form_title": form_title}
    return render(request, "core/products/new_product.html", context)


@login_required
@user_passes_test(is_admin)
def update_product(request, product_id):
    form_title = "Update product details below"
    product = Product.objects.get(pk=product_id)
    form = ProductCreationForm(instance=product)
    if request.method == "POST":
        form = ProductCreationForm(request.POST, instance=product)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                if int(form.cleaned_data["cost"]) > 0:
                    product.profit_rate = abs(int(form.cleaned_data["cost"])) / abs(
                        int(form.cleaned_data["price"])
                    )
                else:
                    product.profit_rate = 0
                product.save()
            except Exception as e:
                print(e)
                context = {
                    "type": "danger",
                    "message": "The product's update could not be saved. Try again later.",
                }
                return render(request, "core/products/response.html", context)
            else:
                context = {
                    "type": "success",
                    "message": "Product successfully updated.",
                }
                response = render(request, "core/products/response.html", context)
                response["HX-TRIGGER"] = "reload_products_table"
                return response

    context = {"form": form, "form_title": form_title, "product": product}
    return render(request, "core/products/new_product.html", context)


@login_required
@user_passes_test(is_admin)
def remove_a_product_question(request, product_id):
    product = Product.objects.get(pk=product_id)
    context = {"product": product}
    return render(request, "core/products/remove_a_product_question.html", context)


@login_required
@user_passes_test(is_admin)
def do_remove_a_product(request, product_id):
    product = Product.objects.get(pk=product_id)
    product.delete()
    context = {
        "type": "success",
        "message": f"Product '{product}' successfully removed.",
        "product": product,
    }
    response = render(request, "core/products/response.html", context)
    response["HX-TRIGGER"] = "reload_products_table"
    return response


@login_required
@user_passes_test(is_admin)
def sales(request):
    context = {}
    return render(request, "core/sales/sales.html", context)


@login_required
@user_passes_test(is_admin)
def sales_summary(request):
    stock_info = Product.objects.all().aggregate(sum_stock=Sum("stock"))
    cost_info = Product.objects.all().aggregate(sum_cost=Sum("cost"))
    sales_info = Product.objects.all().aggregate(sum_sales=Sum("price"))
    context = {
        "stock_sum": stock_info["sum_stock"],
        "cash_invested": cost_info["sum_cost"],
        "after_sales": sales_info["sum_sales"],
        "profit": sales_info["sum_sales"] - cost_info["sum_cost"],
    }
    return render(request, "core/sales/summary.html", context)


@login_required
@user_passes_test(is_admin)
def sales_products(request):
    products = Product.objects.filter(Q(stock__gt=0))
    context = {
        "products": [
            {
                "id": product.pk,
                "name": product.name,
                "stock": product.stock,
                "price": product.price,
            }
            for product in products
        ],
    }
    return render(request, "core/sales/products_for_sale_table.html", context)
