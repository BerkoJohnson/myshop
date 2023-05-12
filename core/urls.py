from django.urls import include, path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="base"),
    path(
        "products/",
        include(
            [
                path("", views.products_home, name="products"),
                path("load-products/", views.load_products, name="load-products"),
                path(
                    "<uuid:product_id>/update-stocks",
                    views.update_product_stock,
                    name="update-product-stock",
                ),
                path("import-products/", views.import_products, name="import-products"),
                path(
                    "import-products/do",
                    views.do_import_products,
                    name="do-import-products",
                ),
                path(
                    "import-products/track_progress/<task_id>",
                    views.track_import_progress,
                    name="import-products-status",
                ),
                path(
                    "remove-products/",
                    views.remove_all_products,
                    name="remove-products",
                ),
                path(
                    "remove-products/question",
                    views.remove_all_products_question,
                    name="remove-products-question",
                ),
                path(
                    "remove-products/do",
                    views.do_remove_products,
                    name="do-remove-products",
                ),
                path(
                    "remove-products/track_progress/<task_id>",
                    views.track_remove_product_progress,
                    name="remove-products-status",
                ),
                path(
                    "get-product-action-buttons",
                    views.get_product_action_buttons,
                    name="get-product-action-buttons",
                ),
                path(
                    "add-product",
                    views.add_product,
                    name="add-product",
                ),
                path(
                    "<uuid:product_id>/update-product",
                    views.update_product,
                    name="update-product",
                ),
                path(
                    "<uuid:product_id>/remove-product",
                    views.remove_a_product_question,
                    name="remove-a-product-question",
                ),
                path(
                    "<uuid:product_id>/remove-product/do",
                    views.do_remove_a_product,
                    name="do-remove-a-product",
                ),
            ]
        ),
    ),
    path(
        "purchases/",
        include(
            [
                path("", views.sales, name="sales"),
                path("summary/", views.sales_summary, name="sales-summary"),
                path("sell-products/", views.sales_products, name="sales-products"),
                path("sell-products/load/", views.load_sales_products, name="load-sales-products"),
                path("make-purchase/",views.make_purchase, name="make-purchase"),
                path("shop-cart/",views.shop_cart, name="shop-cart")
            ]
        ),
    ),
]
