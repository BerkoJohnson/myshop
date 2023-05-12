from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
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
import json


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
def orders(request):
    context = {}
    return render(request, "core/orders/orders.html", context)


@login_required
@user_passes_test(is_admin)
def orders_summary(request):
    stock_info = Product.objects.all().aggregate(sum_stock=Sum("stock"))
    cost_info = Product.objects.all().aggregate(sum_cost=Sum("cost"))
    orders_info = Product.objects.all().aggregate(sum_orders=Sum("price"))
    context = {
        "stock_sum": stock_info["sum_stock"],
        "cash_invested": cost_info["sum_cost"],
        "after_orders": orders_info["sum_orders"],
        "profit": orders_info["sum_orders"] - cost_info["sum_cost"],
    }
    return render(request, "core/orders/summary.html", context)


@login_required
@user_passes_test(is_admin)
def orders_products(request):
    products = Product.objects.filter(Q(stock__gt=0)).order_by("name")

    paginator = Paginator(products, 10)

    page_obj = paginator.get_page(1)
    context = {
        "page_obj": page_obj,
    }
    return render(request, "core/orders/products_for_sale_table.html", context)


@login_required
@user_passes_test(is_admin)
def load_orders_products(request):
    products = Product.objects.filter(Q(stock__gt=0)).order_by("name")

    if request.GET.get("p") is not None and request.GET.get("p") != "":
        page = int(request.GET.get("p"))

    if request.GET.get("s") is not None and request.GET.get("s") != "":
        products = products.filter(Q(name__icontains=request.GET.get("s"))).order_by(
            "name"
        )

    paginator = Paginator(products, 10)

    page_obj = paginator.get_page(page)

    context = {"page_obj": page_obj}
    return render(request, "core/orders/products_with_stocks_table_rows.html", context)


@login_required
@user_passes_test(is_admin)
def make_order(request):
    items = []
    if request.method == "POST":
        items = [json.loads(item) for item in request.POST.getlist("items")]

        if len(items) == 0:
            msg_type = "danger"
            message = "No items in the cart. Add items to the cart and make payment."
            context = {"type": msg_type, "message": message}
            return render(request, "core/orders/order_made.html", context)

        new_order_items = []
        # create order items
        for item in items:
            product_check_valid = True
            product = Product.objects.get(id=item.get("id"))

            # if the product does not exist
            if product is None:
                product_check_valid = False

            # else if stock is less than the required quantity
            elif item.get("qty") > product.stock:
                product_check_valid = False

            # else if the calculated total price send is wrong,
            elif float(item.get("total_price")) != product.price * int(item.get("qty")):
                product_check_valid = False

            # if item passed the product checks
            if product_check_valid:
                new_order_items.append({"product": product, "item": item})

        if len(items) != len(new_order_items):
            message = "Something went wrong. Your order could not be initiated."
            context = {"type": "danger", "message": message}
            return render(request, "core/orders/order_made.html", context)

        with transaction.atomic():
            try:
                # create new order
                order_obj = Order.objects.create(
                    user=request.user,
                )
                for ordItem in new_order_items:
                    order_item = OrderItem.objects.create(
                        order=order_obj,
                        product=ordItem["product"],
                        qty_bought=ordItem["item"].get("qty"),
                        paid_amount=float(item.get("total_price")),
                    )

                    # update each product's stock to reflect the last order
                    ordItem["product"].stock -= ordItem["item"].get("qty")
                    ordItem["product"].save()

                # update overall amount paid in this order
                order_obj.overall_amount_paid = sum(
                    float(item.get("total_price")) for item in items
                )
            except Exception as e:
                # if anything goes wrong, all changes will be reversed.
                message = "Your order was not successfully. Try again at a later time."
                msg_type = "danger"
            else:
                # order was successful
                message = f"Your order totaling GHs {order_obj.overall_amount_paid} was successful. Thank you."
                msg_type = "success"
                context = {"type": msg_type, "message": message}
                response = render(request, "core/orders/order_made.html", context)
                response["HX-TRIGGER"] = "reload_products_with_stocks"
                return response

        context = {"type": msg_type, "message": message}
        return render(request, "core/orders/order_made.html", context)


@login_required
@user_passes_test(is_admin)
def shop_cart(request):
    return render(request, "core/orders/cart_table.html")


@login_required
@user_passes_test(is_admin)
def get_todays_orders(request):
    return render(request, "core/orders/cart_table.html")


@login_required
@user_passes_test(is_admin)
def out_of_stock(request):
    products = Product.objects.filter(Q(stock=0)).order_by("name")

    paginator = Paginator(products, 10)

    page_obj = paginator.get_page(1)
    context = {
        "page_obj": page_obj,
    }
    return render(request, "core/orders/out_of_stock.html", context)


@login_required
@user_passes_test(is_admin)
def load_out_of_stock(request):
    products = Product.objects.filter(Q(stock=0)).order_by("name")

    # if page is set
    if request.GET.get("p") is not None and request.GET.get("p") != "":
        page = int(request.GET.get("p"))

    # if search term is set
    if request.GET.get("s") is not None and request.GET.get("s") != "":
        products = products.filter(Q(name__icontains=request.GET.get("s"))).order_by(
            "name"
        )

    paginator = Paginator(products, 10)

    page_obj = paginator.get_page(page)

    context = {"page_obj": page_obj}
    return render(request, "core/orders/out_of_stock_items.html")
