
from django.urls import include, path
from . import views

app_name = 'sales'

urlpatterns = [
    path("", views.index, name="base"),
    # path("products/", include([
    #     path('', views.products_home, name="products"),
    #     path('<uuid:product_id>/update-stocks',
    #          views.update_product_stock, name="update-product-stock"),
    #     # update_product_stock
    # ]))
]
