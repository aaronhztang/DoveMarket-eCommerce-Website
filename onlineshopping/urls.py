from django.urls import path
from onlineshopping import views
from django.conf.urls import url, include

urlpatterns = [
    path('home', views.home, name='home'),
    path('retrieveHomeProducts', views.retrieve_home_products),
    path('sell', views.post_product_action, name='sell'),
    path('shoppingCart', views.shopping_cart_action, name='shoppingCart'),
    path('searchproduct', views.search_product, name='searchproduct'),
    path('photo/<int:id>', views.get_photo, name='photo'),
    path('add_product/<int:id>', views.add_product_action, name='add_product'),
    path('payment', views.pay_action, name='payment'),
    path('minusQuantity', views.minusQuantity_action),
    path('plusQuantity', views.plusQuantity_action),
    path('account', views.account, name='account'),
    path('edit_profile', views.edit_profile, name='edit_profile'),
    url(r'^paypal/', include('paypal.standard.ipn.urls')),
    url('payment_done', views.payment_done_action, name='payment_done'),
    path('delete_product/<int:id>', views.delete_product, name='delete_product'),
    path('product_shipped/<int:id>', views.product_shipped, name='product_shipped'),
    path('product_unship/<int:id>', views.product_unship, name='product_unship'),
]