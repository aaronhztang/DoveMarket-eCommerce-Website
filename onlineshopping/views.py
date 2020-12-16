import sys
import datetime
from collections import Counter
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core import serializers
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.utils import timezone, dateformat
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from paypal.standard.forms import PayPalPaymentsForm
from onlineshopping.forms import PostProductForm,EditAccount
from onlineshopping.models import Profile, Product,Cart_Item, Order
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
import json
from math import ceil

TIME_RANGE_FILTER = ['last day', 'last week', 'last month', 'all']
TIME_RANGE_DAYS = {'last day': 1, 'last week': 7, 'last month': 30, 'all': sys.maxsize}
BEST_SELLING_TOP = 6


def home(request):
    if request.user.is_authenticated:
        if not Profile.objects.filter(user=request.user).exists():
            my_profile = Profile()
            my_profile.user = request.user
            my_profile.last_name = request.user.last_name
            my_profile.first_name = request.user.first_name
            my_profile.email = request.user.email
            my_profile.save()
            
    if request.method == 'GET':
        return render(request, 'onlineshopping/home.html', {})


def construct_json(products):
    response_data = []
    for prod in products:
        has_photo = True
        if not prod.product_photo:
            has_photo = False
        p = {
            'id': prod.id,
            'name': prod.product_name,
            'description': prod.description,
            'price': prod.price,
            'quant': prod.available_quantity,
            'has_photo': has_photo,
        }
        response_data.append(p)
    response_json = json.dumps(response_data)
    return response_json

def retrieve_home_products(request):
    best_selling_products = bestSellingProduct_action()
    response_json = construct_json(best_selling_products)
    response = HttpResponse(response_json, content_type='application/json')
    response['Access-Control-Allow-Origin'] = '*'
    return response

def timeFilter(products, time_range):
    cur_time = datetime.date.today()
    results = []
    for prod in products:
        if (cur_time - prod.create_time.date()).days <= TIME_RANGE_DAYS[time_range]:
            results.append(prod)
    return results
        
def priceFilter(products, max_price):
    results = []
    for prod in products:
        if prod.price <= max_price:
            results.append(prod)
    return results

def priceRange(products):
    min = sys.maxsize
    max = 0
    for prod in products:
        if prod.price > max:
            max = prod.price
        if prod.price < min:
            min = prod.price
    return min, max

def bestSellingProduct_action():
    all_orders = Order.objects.all()
    product_count = {} # key: product ID; value: number of quantity ordered
    # count the quantity items ordered for each product
    for o in all_orders:
        id = o.product.id
        quantity = o.ordered_quantity
        # check if this product is still available
        if (Product.objects.get(id=id).available_quantity == 0):
            continue
        if (o.status == 'O'): 
            continue
        if id not in product_count:
            product_count[id] = quantity
        else:
            product_count[id] += quantity
    # sort product_count based on value in descending order
    sorted_product = dict(Counter(product_count).most_common(BEST_SELLING_TOP))
    # return best selling products
    products = []
    for key,_ in sorted_product.items():
        products.append(Product.objects.get(id=key))
    return products


def check_availability(products):
    return_list = []
    for p in products:
        if p.available_quantity != 0: 
            return_list.append(p)
    return return_list

def search_product(request):
    context = {}
    products = Product.objects.all() # all products in database
    avail_products = check_availability(products) # products are available now; quant > 0
    # determine the min/max price
    min, max = priceRange(avail_products)
    if request.method == 'GET':
        context = {'products': avail_products, 'max_price': max, 'min_price': min, 'default': max}
        return render(request, "onlineshopping/searchproduct.html", context)
    else: # if there is any filter requirement
        # validate input
        if 'product_name' not in request.POST:
            context['errors'] = ["You must include product_name as a key in post request."]
            return render(request, "onlineshopping/searchproduct.html", context)

        if 'time_range' not in request.POST or not request.POST['time_range']:
            context['errors'] = ["You must include time_range as a key in post request."]
            return render(request, "onlineshopping/searchproduct.html", context)
        
        if request.POST['time_range'] not in TIME_RANGE_FILTER:
            context['errors'] = ["You time_range value is not valid."]
            return render(request, "onlineshopping/searchproduct.html", context)
        
        if 'price_range' not in request.POST:
            context['errors'] = ["You must include price_range as a key in post request."]
            return render(request, "onlineshopping/searchproduct.html", context)

        max_price = sys.maxsize
        try:
            max_price = int(request.POST['price_range'])
        except ValueError:
            context['errors'] = ["max price must be an integer"]
            return render(request, "onlineshopping/searchproduct.html", context)

        return_list = []
        if request.POST['product_name']:
            # keywords match
            keywords = request.POST['product_name'].split(" ")
            for prod in avail_products:
                prod_name = prod.product_name.split(" ")
                for w in keywords:
                    if w in prod_name:
                        return_list.append(prod)
                        break
        else:
            return_list = avail_products
        
        # time range filter
        return_list = timeFilter(return_list, request.POST['time_range'])
        # price filter
        return_list = priceFilter(return_list, max_price)

        if len(return_list)==0:
                context['Info'] = 'There is no matching product'
        context['products'] = return_list
        context['min_price'] = min
        context['max_price'] = max
        context['default'] = max
        if max_price != sys.maxsize:
            context['default'] = max_price
        return render(request, 'onlineshopping/searchproduct.html', context)

@login_required
def add_to_cart(request, id):
    if not isinstance(id, int):
        print ("ID must be an integer")
        context = {'products': Product.objects.all()}
        return context
    id = id - 1
    quant = 0
    try:
        quant = int(request.POST["product_quantity"])
    except ValueError:
        print ("quantity must be an integer")
        context = {'products': Product.objects.all()}
        return context
    product_info = Product.objects.all()[id]
    if quant > product_info.available_quantity:
        print ("Not enough quantity")
        context = {'products': Product.objects.all(), 'card_errors': ["Not enough quantity"]}
        return context
    # check if such product already exists
    try:
        obj = Cart_Item.objects.get(product=product_info, buyer=request.user)
        obj.saved_quantity = quant
        obj.save()
    except Cart_Item.DoesNotExist:
        new_cart_product = Cart_Item.objects.create(product=product_info, buyer=request.user, saved_quantity = quant)
        new_cart_product.save()

    # return full list of products that are currently avaiable:
    context = {'products': check_availability(Product.objects.all())}
    return context

@login_required
def add_to_payment_list(request, id):
    # create an order for this product
    orders = Order.objects.filter(buyer=request.user,status='O')
    for order in orders:
        order.delete()

    product = Product.objects.get(id = id)
    buyer = request.user
    quant = 0
    try:
        quant = int(request.POST["product_quantity"])
    except ValueError:
        print ("quantity must be an integer")
        context = {'products': Product.objects.all()}
        return context
    order = Order(product=product, buyer=buyer, status='O',ordered_quantity=quant)
    order.save()
    return pay_action(request)
    
    

# Process the actions of "add to cart" and "buy" in search product page
@login_required
def add_product_action(request, id):
    products = Product.objects.all()
    avail_products = check_availability(products)
    # request method must be post
    if request.method == 'POST':
        if "cart_search" in request.POST: # coming from search page
            context = add_to_cart(request, id)
            context["message"] = ["Sucessfully added to the cart"]
            return render(request, "onlineshopping/searchproduct.html", context)
        if "cart" in request.POST: # coming from home page
            context = add_to_cart(request, id)
            context["message"] = ["Sucessfully added to the cart"]
            return render(request, 'onlineshopping/home.html', context)
        elif "buy" in request.POST:
            return add_to_payment_list(request, id)
        else:
            print ("Invalid button value")
    if request.method == 'GET':
        return render(request, "onlineshopping/searchproduct.html", {'products': avail_products})

@login_required
@ensure_csrf_cookie
def shopping_cart_action(request):
    if request.method != 'POST':
        context = {}
        user = request.user
        context['items_in_Cart'] = []
        for cart_item in Cart_Item.objects.filter(buyer=user):
            if cart_item.product.available_quantity > 0:
                context['items_in_Cart'].append(cart_item)
                
        return render(request, 'onlineshopping/shoppingCart.html',context)
    
    if not 'ids' in request.POST or not request.POST['ids']:
        return _my_json_error_response("You must have a list of ids that needs action.")

    orders = Order.objects.filter(buyer=request.user,status='O')
    for order in orders:
        order.delete()

    ids = request.POST['ids'].split(",")
    for id in ids:
        cartItem = get_object_or_404(Cart_Item, buyer=request.user, id=id)
        if request.POST['action']=="buy":
            order = Order(product=cartItem.product, buyer=cartItem.buyer, status='O',ordered_quantity=cartItem.saved_quantity, create_time=timezone.now())
            order.save()
        cartItem.delete()
    
    response_json = json.dumps(ids)
    response = HttpResponse(response_json, content_type='application/json')
    response['Access-Control-Allow-Origin'] = '*'
    return response

def _my_json_error_response(message, status=200):
    # You can create your JSON by constructing the string representation yourself (or just use json.dumps)
    response_json = '{ "error": "' + message + '" }'
    return HttpResponse(response_json, content_type='application/json', status=status)


@login_required
@ensure_csrf_cookie
def minusQuantity_action(request):
    if not 'id' in request.POST or not request.POST['id']:
        return _my_json_error_response("You must have a item to edit its quantity.")
    cartItem_id = request.POST['id']
    cartItem = get_object_or_404(Cart_Item, id=cartItem_id)
    cartItem.saved_quantity -= 1
    cartItem.save()

    response_json = json.dumps({ 'quantity': cartItem.saved_quantity })
    response = HttpResponse(response_json, content_type='application/json')
    response['Access-Control-Allow-Origin'] = '*'
    return response
    
@login_required
@ensure_csrf_cookie
def plusQuantity_action(request):
    if not 'id' in request.POST or not request.POST['id']:
        return _my_json_error_response("You must have a item to edit its quantity.")
    cartItem_id = request.POST['id']
    cartItem = get_object_or_404(Cart_Item, id=cartItem_id)
    if cartItem.saved_quantity < cartItem.product.available_quantity:
        cartItem.saved_quantity += 1
        cartItem.save()

    response_json = json.dumps({ 'quantity': cartItem.saved_quantity })
    response = HttpResponse(response_json, content_type='application/json')
    response['Access-Control-Allow-Origin'] = '*'
    return response


@login_required
def pay_action(request):
    context = {}
    user = request.user
    context['items_to_buy'] = []
    context['message'] = []
    for item in Order.objects.filter(buyer=user,status='O'):
        if item.product.available_quantity >= item.ordered_quantity:
            context['items_to_buy'].append(item)
        else:
            context['message'].append(item.product.product_name + ' is out of stock!')

    amount = 0
    for item in context['items_to_buy']:
        amount += item.product.price*item.ordered_quantity

    host = request.get_host()
    paypal_dict = {
        'business': settings.PAYPAL_RECEIVER_EMAIL,
        'amount': amount,
        'item_name': 'Item_Name_xyz',
        'invoice': 'Payment Invoice',
        'currency_code': 'USD',
        'return_url': 'http://{}{}'.format(host, reverse('payment_done')),
        #'cancel_return': 'http://{}{}'.format(host, reverse('payment_canceled')),
    }
    context['amount'] = amount
    context['form'] = PayPalPaymentsForm(initial=paypal_dict)
    return render(request, 'onlineshopping/payment.html', context)

@login_required
@csrf_exempt
def payment_done_action(request):
    user = request.user
    for item in Order.objects.filter(buyer=user,status='O'):
        item.status = 'C'
        item.save()
        product = get_object_or_404(Product, product_name=item.product.product_name)
        product.available_quantity -= item.ordered_quantity
        product.save()
    return render(request, 'onlineshopping/home.html')

@login_required
def post_product_action(request):
    if request.method != 'POST':
        return render(request, 'onlineshopping/sell.html', {'form': PostProductForm()})
    
    product = Product()
    product.post_user = request.user
    product.create_time=timezone.now()

    post_form = PostProductForm(request.POST, request.FILES, instance=product)
    if not post_form.is_valid():
        return render(request, 'onlineshopping/sell.html', {'form': post_form})

    post_form.save()
    return render(request, 'onlineshopping/sell.html', {'form': PostProductForm(),'message': ["Successfully posted!"]})


def get_photo(request, id):
    item = get_object_or_404(Product, id=id)
    print('Picture #{} fetched from db: {} (type={})'.format(id, item.product_photo, type(item.product_photo)))

    # Maybe we don't need this check as form validation requires a picture be uploaded.
    # But someone could have delete the picture leaving the DB with a bad references.
    if not item.product_photo:
        raise Http404
    return HttpResponse(item.product_photo, content_type=item.content_type)


@login_required
def account(request):
    context = {}
    if Profile.objects.filter(user=request.user).exists():
        my_profile = Profile.objects.get(user=request.user)
    else:
        my_profile = Profile()
        my_profile.user = request.user
        my_profile.last_name = request.user.last_name
        my_profile.first_name = request.user.first_name
        my_profile.email = request.user.email
        my_profile.save()

    context['profile'] = my_profile

    products= Product.objects.all().filter(post_user=request.user).exclude(available_quantity=0).order_by('-create_time')
    n= len(products)
    nSlides= n//4 + ceil((n/4) + (n//4))
    context['numberSell'] = nSlides
    context['rangeSell'] = range(1,nSlides)
    context['product'] = products

    orders= Order.objects.all().filter(buyer=request.user).order_by('-create_time')
    n= len(orders)
    nSlides= n//4 + ceil((n/4) + (n//4))
    context['numberBuy'] = nSlides
    context['rangeBuy'] = range(1,nSlides)
    context['order'] = orders

    sold= Order.objects.all().filter(product__post_user=request.user).exclude(status='O').order_by('-create_time')
    n= len(orders)
    nSlides= n//4 + ceil((n/4) + (n//4))
    context['numberSold'] = nSlides
    context['rangeSold'] = range(1,nSlides)
    context['sold'] = sold
    
  
    return render(request, 'onlineshopping/account.html', context)

@login_required
def edit_profile(request):
    context = {}
    my_profile = Profile.objects.get(user=request.user)
    if request.method == 'GET':
        context['profile'] = my_profile
        context['form'] = EditAccount(instance=my_profile)
        return render(request, 'onlineshopping/editprofile.html', context)
    
    form = EditAccount(request.POST, instance=my_profile)

    if not form.is_valid():
        context['profile'] = my_profile
        context['form'] = form
        return render(request, 'onlineshopping/editprofile.html', context)

    form.save()

    return redirect('account')

@login_required
def delete_product(request, id):
    context = {}
    product = Product.objects.get(id=id)
    product.available_quantity = 0
    product.save()

    return redirect('account')

@login_required
def product_shipped(request, id):
    context = {}
    order = Order.objects.get(id=id)
    order.status = 'S'
    order.save()
    
    return redirect('account')

@login_required
def product_unship(request, id):
    context = {}
    order = Order.objects.get(id=id)
    order.status = 'C'
    order.save()
    
    return redirect('account')
# plus and minus restricts
# css
