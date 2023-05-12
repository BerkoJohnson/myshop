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
        "orders/",
        include(
            [
                path("", views.orders, name="orders"),
                path("summary/", views.orders_summary, name="orders-summary"),
                path("sell-products/", views.orders_products, name="orders-products"),
                path("sell-products/load/", views.load_orders_products, name="load-orders-products"),
                path("make-order/",views.make_order, name="make-order"),
                path("shop-cart/",views.shop_cart, name="shop-cart"),
                path("out-of-stock/",views.out_of_stock, name="out-of-stock"),
                path("out-of-stock/load",views.load_out_of_stock, name="load-out-of-stock"),
            ]
        ),
    ),
]
