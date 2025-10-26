from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from forms import RegistrationForm, RatingForm
from . import models
from django.db.models import Q, Min, Max, Avg
from . import forms
from . import sslcommerz
# Create your views here.

# Manual User Authentication
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            redirect('')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, '')

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration Successful!")
            return redirect('')
    else:
        form = RegistrationForm()

    return render(request, '', {'form': form})

def logout_view(request):
    logout(request)
    return render('')

#homepage

def home(request):
    featured_products = models.Product.objects.filter(available= True).order_by('-created_at')[:8] #descending order
    categories  = models.Category.objects.all()

    return render(request, '', {'featured_products': featured_products, 'categories': categories})

# product list page

def product_list(request, category_slug = None):
    category = None
    categories = models.Category.objects.all()
    products = models.Product.objects.all()

    if category_slug:
        category = get_object_or_404(models.Category, category_slug)
        products = products.filter(category = category)

    min_price = products.aaggregate(Min('price'))['price__min']
    max_price = products.aaggregate(Max('price'))['price__max']

    if request.GET.get('min_price'):
        products = products.filter(price_gte=request.GET.get('min_price'))

    if request.GET.get('max_price'):
        products = products.filter(price_lte=request.GET.get('max_price'))

    if request.GET.get('rating'):
        products = products.annotate(avg_rating = Avg('ratings__rating')).filter(avg_rating = request.GET.get('rating'))
    # temp variable --> average rating
    # Avg
    # ratings related_name ke use kore rating model er rating value ke access korlam
    # avg_rating == user er filer kora rating er shathe
    if request.GET.get('search'):
        query = request.GET.get('search')
        products = products.filter(
            Q(name__icontains = query) |
            Q(description__icontains = query) | #incomplete
            Q(category_name__icontains = query)
        )

    return render(request, '', {
        'category' : category,
        'categories' : categories,
        'products' : products,
        'min_price' : min_price,
        'max_price' : max_price
    })

# product details page

def product_detail(request, slug):
    product = get_object_or_404(models.Product, slug = slug, available = True)
    related_products = models.Product.objects.filter(category = product.category).exclude(id = product.id)

    user_rating = None

    if request.user.is_authenticated:
        try:
            user_rating = models.Rating.objects.get(product = product, user = request.user)
        except models.Rating.DoesNotExist:
            pass

    rating_form = RatingForm(instance = user_rating)

    return render(request, '', {
        'product' : product,
        'related_products' : related_products,
        'user_rating' : user_rating,
        'rating_form' : rating_form
    })

# Rate Product

# logged in user, Purchase koreche kina

def rate_product(request, product_id):
    product = get_object_or_404(models.Product, id=product_id)

    ordered_items = models.OrderItem.objects.filter(
        order__user = request.user,
        product = product,
        order__paid = True
    )

    if not ordered_items.exists(): #order kore nai
        messages.warning(request, 'You can only rate products you have purchased!')
        return redirect('')
    try:
        rating = models.Rating.objects.get(product = product, user = request.user)
    except models.Rating.DoesNotExist:
        rating = None

    #jodi rating age diye thake taile rating form ager rating diye fill up kora thakbe. she khetre instance = user rating hoye jabe
    #jodi rating nakora thake taile instance = None thakbe jate user rating dite pare
    if request.method == 'POST':
        form = RatingForm(request.POST, instance= rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product
            rating.user = request.user
            rating.save()
            return redirect('')
        else:
            form = RatingForm(instance= rating)

        return render(request, '', {
            'form': form,
            'product': product
        })
    
def cart_add(request, product_id):
    product = get_object_or_404(models.Product, id=product_id)

    # jodi thake taile oi cart ta check korbo
    try:
        cart = models.Cart.objects.get(user = request.user)
    # jodi na thake, taile cart ekta banabo
    except models.Cart.DoesNotExist:
        cart = models.Cart.objects.create(user = request.user)

    # cart e item add korbo
    # item already is in cart
    try:
        cart_item = models.CartItem.objects.get(cart = cart, product = product)
        cart_item.quantity += 1
        cart_item.save()

    # item is not in cart
    except models.CartItem.DoesNotExist:
        models.CartItem.objects.create(cart = cart, product = product, quantity = 1)

    messages.success(request, f"{product.name} has ben added to your cart!")
    return redirect(request ,'')

# cart update
# cart item quantity increase/decrease korte parbo

def cart_update(request, product_id):
    #cart konta
    #cart er item konta
    # stock er sathe compare kora

    cart = get_object_or_404(models.Cart, user = request.user)
    product = get_object_or_404(models.Product, product_id)
    cart_item = get_object_or_404(models.CartItem, cart = cart, product = product)

    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        cart_item.delete()
        messages.success(request, f"Item has been removed from the cart")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"Cart updated successfully")

def cart_remove(request, product_id):
    cart = get_object_or_404(models.cart, user = request.user)
    product= get_object_or_404(models.Product, id = product_id)
    cart_item = get_object_or_404(models.CartItem, cart = cart, product = product)

    cart_item.delete()
    messages.success(request, f"{product.name} has been successfully removed from your cart")
    return redirect('')

def cart_detail(request):
    #user er kono cart nai
    #user er cart ase
    try:
        cart = models.Cart.objects.get(user = request.user)
    except: models.Cart.objects.create(user = request.user)

    return render(request, '', {'cart':cart})

# checkout
# cart er data gula niye ashbo
# Total taka
# Payment option --> payment gateway te niye jabo
# Product --> Cart Item --> Order Item

def checkout(request):
    try:
        cart = models.Cart.objects.get(user = request.user)
        if not cart.items.exists():
            messages.warning(request, 'Your cart is empty')
            return redirect()
    except models.Cart.DoesNotExist:
        messages.warning(request, 'Cart does not exist')
        return redirect('')
    
    # checkout form ta fillup korbe
    if request.method == 'POST':
        form = forms.CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False) # Order form create hobe kintu data database e jabe na
            order.user = request.user
            order.save() #order kora hoye gese

            for item in cart.items.all():
                models.OrderItem.objects.create(
                    order = order,
                    product = item.product, # cart item e ekhon order item
                    price = item.product.price, # product er main price e order item er main price
                    quantity = item.quantity # cart item er quantity e hocche order item er quantity
                )

            # order kora done finally
            # cart er ar kono value e nai
            cart.items.all().delete() #cart er item gula delete kore dilam

            return render(request, '', {
                'cart' : cart,
                'form' : form
            })
        
# Payment related khela
# 0.Payment process --> SSL Commerz er window dekhabe, email confirmation pathano
# 1.Payment success
# 2.Payment failed
# 3.Payment cancel

def payment_process(request):
    #session
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('')
    
    order = get_object_or_404(models.Order, id=order_id)
    payment_data = sslcommerz.generate_sslcommerz_payment(request, order)

    if payment_data['status'] == 'SUCCESS' :
        return redirect()
    else:
        messages.erro(request, 'Payment gateway error')

def payment_success(request, order_id):
    order = get_object_or_404(models.Order, id = order_id, user=request.user)
# order ta paid
# order er status --> processing
# product er stock komiye dibo
# transaction id
    order.paid = True
    order.status = 'processing'
    order.transaction_id = order.id
    order.save()
    order_items = order.order_items.all()
    for item in order_items:
        product = item.product
        product.stock -= item.quantity

        if product.stock < 0:
            product = 0
        product.save()

    # send confirmation mail
    messages.success(request, 'Payment Successful!')
    return render(request, '', {'order':order})

def payment_fail(request, order_id):
    order = get_object_or_404(models.Order, id = order_id, user=request.user)
    order.status = 'canceled'
    order.save()
    return redirect('')

def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id = order_id)
    order.status = 
    order.save()
    return redirect('cart_detail')

def profile(request):
    tab = request.GET.get('tab')
    orders = Order.objects.filter(user = request.user)
    