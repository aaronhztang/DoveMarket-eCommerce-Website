from django.db import models
from django.contrib.auth.models import User
from phone_field import PhoneField


class Profile(models.Model):
    user = models.OneToOneField(User, default=None, blank=False, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=20, default='team', null=True)
    last_name = models.CharField(max_length=20, default='2', null=True)
    email = models.EmailField(max_length = 254, default='team2@cmu.com', null=True)
    phone = PhoneField(blank=True, help_text='Contact phone number', default='888-888-8888', null=True) 
    address = models.CharField(blank=True, max_length=200, default='CMU', null=True)
    city = models.CharField(blank=True, max_length=30, default='Pittsburgh', null=True)
    state = models.CharField(blank=True, max_length=20, default='PA', null=True)
    zip_code = models.CharField(blank=True, max_length=10, default='15213', null=True)
    country = models.CharField(blank=True, max_length=30, default='US', null=True)


class Product(models.Model):
    # product name is not allowed to be empty
    product_name = models.CharField(max_length=100, default=None, blank=False)
    # product description is allowed to be empty
    description = models.CharField(max_length=1000, default=None, blank=True)
    # product_photo is allowed to be empty
    product_photo = models.FileField(default=None, blank=True, null=True)
    price = models.IntegerField(default=None, blank=False)
    # remaining available quantity of the product, not allowed to be empty
    available_quantity = models.IntegerField(default=None, blank=False)
    # user that posts the product, not allowed to be empty
    post_user = models.ForeignKey(User, default=None, blank=False, on_delete=models.PROTECT)
    content_type = models.CharField(max_length=50, default=None, null=True)
    create_time = models.DateTimeField(auto_now_add=True, auto_now=False)

class Order(models.Model):
    product = models.ForeignKey(Product, default=None, blank=False, on_delete=models.PROTECT)
    buyer = models.ForeignKey(User, default=None, blank=False, on_delete=models.PROTECT)
    # choices for status: the first element in tuple is the actual value stored in model,
    # the second element in tuple is the human readable value that can display in web
    STATUS_CHOICES = [
        ('O', 'Ordered'),
        ('C', 'Paid'),
        ('S', 'Shipped'),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='O', blank=False)
    # ordered quantity of the product, not allowed to be empty
    ordered_quantity = models.IntegerField(default=1, blank=False)
    # automatically save the time to now when object is created. Time won't be automatically changed
    # when we save it other than the case of first creating it
    create_time = models.DateTimeField(auto_now_add=True, auto_now=False)

class Cart_Item(models.Model):
    product = models.ForeignKey(Product, default=None, blank=False, on_delete=models.PROTECT)
    # who save the product into cart
    buyer = models.ForeignKey(User, default=None, blank=False, on_delete=models.PROTECT)
    # how many items were saved into the cart
    saved_quantity = models.IntegerField(default=1, blank=False)