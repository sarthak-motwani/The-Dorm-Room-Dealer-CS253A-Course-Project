from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import auth
from django.contrib.auth.decorators import login_required
from items.models import Item
from .models import Detail
from django.core.mail import send_mail
from datetime import datetime
from django.utils import timezone
import datetime
from django.core.paginator import Paginator
from .models import CustomUser
from django.db.models import F

# function to implement the login facility


def login(request):
    if request.method == 'POST':
        username = request.POST.get('un', '')
        pwd = request.POST.get('pa', '')
        user = auth.authenticate(username=username, password=pwd)

        if user == None:
            messages.info(request, "Invalid Username/Password")
            return redirect('login')
        else:
            auth.login(request, user)
            return redirect("home")

    else:
        return render(request, 'login.html')

# function to implement the registration utility for a new user


def register(request):
    if request.method == 'POST':
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        username = request.POST['username']
        # rollno = request.POST['email']
        # mail = rollno + "@iitk.ac.in"
        mail = request.POST['email']
        p1 = request.POST['p1']
        p2 = request.POST['p2']
        profile = request.FILES.get('profile')
        contact = request.POST['contact']
        hall = request.POST['hall']
        if p1 == p2:
            if CustomUser.objects.filter(email=mail).exists():
                messages.info(request, "User with this Email already exists")
                return redirect('register')
            elif CustomUser.objects.filter(username=username).exists():
                messages.info(request, "Username Taken")
                return redirect('register')
            else:
                user = CustomUser.objects.create_user(
                    first_name=firstname, last_name=lastname, email=mail, password=p1, username=username)
                user.add_notification(
                    "Succesfull Registration!")
                user.save()
                obj = Detail(username=username, contact=contact,
                             profile=profile, hall=hall)
                obj.save()
                subject = "The Dorm Room Dealer"
                msg = "Succesfull Registration!"
                to = mail
                res = send_mail(
                    subject, msg, "dormroomdealer@gmail.com", [to])
                if res == 1:
                    return redirect('/')
                # else:
                #     messages.info(request, "Error")
                return redirect('/')
        else:
            messages.info(request, "Password does not match")
            return redirect('register')
    else:
        return render(request, 'register.html')

# logout function


def logout(request):
    auth.logout(request)
    return redirect("login")

# function to logout from the items


def ilogout(request):
    auth.logout(request)
    return redirect("login")

# helper function to update the current status of items on the application


@login_required(login_url='login')
def productStatus(request):

    item = Item.objects.all()
    for i in item:
        try:
            highest_bidder = i.highest_bidder
            if highest_bidder is not None and i.status == "live":
                i.sold = "Bidded"
                i.save()
            elif highest_bidder is not None and i.status == "past":
                i.sold = "Sold"
                i.save()
            elif i.status == "future":
                i.sold = "Yet to be auctioned"
                i.save()
            else:
                i.sold = "Unsold"
                i.save()
        except:
            pass

# helper function to send mails


@login_required(login_url='login')
def sendMail(request):
    now = timezone.now()
    item = Item.objects.filter(end_date__lte=now).filter(
        sold="Sold").filter(sendwinmail="notSent")
    for i in item:
        try:
            # Selecting the attributes of the auction winner

            winnerID = i.highest_bidder
            user_obj = CustomUser.objects.get(id=winnerID)
            winnerEmail = user_obj.email
            winnerUsername = user_obj.username
            CustomUser.add_notification(
                "Succesfull Registration!")

            # -----------------------------------------------------------
            obj = Detail.objects.get(username=winnerUsername)
            winnerContact = obj.contact

            itemMail = i.ownermail
            itemUserobj = CustomUser.objects.get(email=itemMail)
            itemUser = itemUserobj.username

            obj2 = Detail.objects.get(username=itemUser)
            itemContact = obj2.contact
            # -------------------------------------------------------------

            # Mail sent to the highest bidder
            subject = "The Dorm Room Dealer"
            msg = "You have successfuly purchased the item -  " + i.name + ". Email-id of the seller is " + \
                i.ownermail + ". You can contact the seller for further informations at " + itemContact + "."
            user_obj.add_notification(msg)
            to = winnerEmail
            res = send_mail(
                subject, msg, "dormroomdealer@gmail.com", [to])
            if res == 1:
                print("Mail sent")
            else:
                print("Error. Mail not sent.")

            # Mail sent to the seller
            subject = "The Dorm Room Dealer"
            msg = "The email id of the highest bidder of your item - " + i.name + " is " + \
                winnerEmail + " . You can contact them for further informations at " + winnerContact + "."
            itemUserobj.add_notification(msg)
            to = i.ownermail
            res = send_mail(
                subject, msg, "dormroomdealer@gmail.com", [to])
            if res == 1:
                print("Mail sent")
            else:
                print("Error. Mail not sent.")
            i.sendwinmail = "sent"
            i.save()
        except:
            pass

# function to implement the home page of the application, which will show the live bids


@login_required(login_url='login')
def home(request):

    show_notifications_link = True
    user = request.user
    notifications = user.notifications.all()

    # check for how many notifications have field seen false
    num_notifications = 0
    for notification in notifications:
        if notification.seen == False:
            num_notifications = num_notifications+1

    # creating a category search on the top of the home page
    if request.method == "POST":
        category = request.POST.get('category')
    else:
        category = "All categories"

    items = Item.objects.all()
    today = timezone.now()

    # assigning status to each product
    for i in items:

        # if item start_date not mentioned , we take today as the default value
        i.start_date = i.start_date or today
        # if item end_date not mentioned, we take tomorrow as the default value
        i.end_date = i.end_date or today + datetime.timedelta(days=1)

        if (today < i.start_date):
            i.status = "future"
        elif (i.start_date <= today < i.end_date and i.status != "past"):
            i.status = "live"
        else:
            i.status = "past"

        i.save()

    productStatus(request)
    sendMail(request)

    if category != "All categories" and category != None:
        items = Item.objects.filter(status="live").filter(tag=category)
        itemsfuture = Item.objects.filter(status="future").filter(tag=category)
    else:
        items = Item.objects.filter(status="live")
        itemsfuture = Item.objects.filter(status="future")

    sort_by = request.GET.get("sort", "l2h")    
    if sort_by == "l2h":
       items = items.order_by('currentPrice')
       itemsfuture = itemsfuture.order_by('currentPrice')
    elif sort_by == "h2l":
       items = items.order_by('-currentPrice')
       itemsfuture = itemsfuture.order_by('-currentPrice')
    elif sort_by == "sdate":
        items = items.order_by('start_date')
        itemsfuture = itemsfuture.order_by('start_date')    
    elif sort_by == "edate":
        items = items.order_by('end_date')
        itemsfuture = itemsfuture.order_by('end_date') 

    # paginating
    paginator = Paginator(items, 6)  # Show 6 products per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    paginator2 = Paginator(itemsfuture,6)   # Show 6 products per page.
    page_number = request.GET.get('page')
    page_obj2 = paginator2.get_page(page_number)


    return render(request, "home.html", {'page_obj': page_obj, 'page_obj2': page_obj2, 'show_notifications_link': show_notifications_link, "num_notifications": num_notifications})


# function to implement notifications from the Customuser requesting for notifications. Show most recent 10 notifications
@login_required(login_url='login')
def notifications(request):
    user = request.user
    show_notifications_link = False
    notifications = user.notifications.all().order_by('-date')
    # update the status of all notifications with field seen false to be true
    for notification in notifications:
        if notification.seen == False:
            notification.seen = True
            notification.save()
    notifications = notifications[:10]
    # console log all the notifications
    for notification in notifications:
        print(notification)
    print('hello')
    return render(request, "notifications.html", {'notifications': notifications})

# This function mainains a log of the user's history with the application


@login_required(login_url='login')
def dashboard(request):

    show_notifications_link = False

    # Checking if seller stopped the auction beforehand
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
    else:
        item_id = None

    if item_id is not None:
        item = Item.objects.get(id=item_id)
        item.status = "past"
        item.save()

    # Select the bidder attributes to send the mail in case the auction was stopped beforehand

        try:

            winnerID = item.highest_bidder
            user_obj = CustomUser.objects.get(id=winnerID)
            winnerEmail = user_obj.email
            winnerUsername = user_obj.username

            # -----------------------------------------------------------
            obj = Detail.objects.get(username=winnerUsername)
            winnerContact = obj.contact

            itemMail = item.ownermail
            itemUserobj = CustomUser.objects.get(email=itemMail)
            itemUser = itemUserobj.username

            obj2 = Detail.objects.get(username=itemUser)
            itemContact = obj2.contact

            # -------------------------------------------------------------
            # Mail sent to the highest bidder

            subject = "The Dorm Room Dealer"
            msg = "You have successfuly purchased " + item.name+". Email-id of the seller is " + \
                item.ownermail+". You can contact the seller for further informations at " + \
                itemContact + "."
            user_obj.add_notification(msg)
            to = winnerEmail
            res = send_mail(
                subject, msg, "dormroomdealer@gmail.com", [to])
            if res == 1:
                print("Mail sent")
            else:
                print("Error. Mail not sent.")

            # Mail sent to the seller

            subject = "The Dorm Room Dealer"
            msg = "Your item "+item.name+"'s higgest bidder's email id is "+winnerEmail + \
                " . You can contact them for further informations at "+winnerContact + "."
            itemUserobj.add_notification(msg)
            to = item.ownermail
            res = send_mail(
                subject, msg, "dormroomdealer@gmail.com", [to])
            if res == 1:
                print("Mail sent")
            else:
                print("Error. Mail not sent.")
            item.sendwinmail = "sent"
            item.save()
        except:
            pass

    # Setting up the user information

    bidder = request.user
    details = bidder
    username = details.username

    obj3 = Detail.objects.filter(username=username)
    contact = ""
    profile = ""
    hall = ""
    for i in obj3:
        contact = i.contact
        profile = i.profile
        hall = i.hall

    # Setting up the user items history information
    user = request.user
    mail = user.email
    id = user.id
    item_obj = Item.objects.filter(highest_bidder=id)

    biddedlive = item_obj.filter(status="live")
    biddedpast = item_obj.filter(status="past")

    pitem = Item.objects.filter(ownermail=mail).filter(status="past")
    litem = Item.objects.filter(ownermail=mail).filter(status="live")
    fitem = Item.objects.filter(ownermail=mail).filter(status="future")

    # paginating live items
    paginator = Paginator(litem,4)  # Show 4 products per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # paginating future items
    paginator2 = Paginator(fitem, 4)
    page_number = request.GET.get('page')
    page_obj2 = paginator2.get_page(page_number)

    # paginating past items
    paginator3 = Paginator(pitem, 4)
    page_number = request.GET.get('page')
    page_obj3 = paginator3.get_page(page_number)

    # paginating biddedlive items
    paginator4 = Paginator(biddedlive, 4)
    page_number = request.GET.get('page')
    page_obj4 = paginator4.get_page(page_number)

    # paginating biddedpast items
    paginator5 = Paginator(biddedpast, 4)
    page_number = request.GET.get('page')
    page_obj5 = paginator5.get_page(page_number)


    return render(request, "dashboard.html", {'page_obj':page_obj,'page_obj2':page_obj2, 'page_obj3':page_obj3, 'page_obj4':page_obj4, 'page_obj5':page_obj5, "details": details, "contact": contact, "profile": profile, "hall": hall, "show_notifications_link": show_notifications_link})


# function to allow user to edit their details
@login_required(login_url='login')
def edit_profile(request):

    if request.method == 'POST':
        # update the user's details
        user = request.user
        user.first_name = request.POST.get('firstname')
        user.last_name = request.POST.get('lastname')
        user.email = request.POST.get('email')
        user.save()

        # update the user's detail model
        detail = Detail.objects.get(username=user.username)
        detail.contact = request.POST.get('contact')
        if (request.FILES.get('profile')):
            detail.profile = request.FILES.get('profile')
        else:
            detail.profile = detail.profile
        if (request.POST.get('hall')):
            detail.hall = request.POST.get('hall')
        else:
            detail.hall = detail.hall
        detail.save()

        # messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard')

    else:
        # render the edit form
        user = request.user
        detail = Detail.objects.get(username=user.username)

        # initial_values = {'firstname': user.first_name,
        #           'lastname': user.last_name,
        #           'email': user.email,
        #           'contact': detail.contact,
        #           'hall': detail.hall,
        #           'profile': detail.profile}

        # form = EditProfileForm(initial=initial_values)
        return render(request, 'edit_profile.html', {'user': user, 'detail': detail})
