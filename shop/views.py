from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from forms import RegistrationForm, RatingForm
from . import models
from django.db.models import Q, Min, Max, Avg
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