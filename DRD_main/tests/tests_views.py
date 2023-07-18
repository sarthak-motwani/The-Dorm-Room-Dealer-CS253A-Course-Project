from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import Detail
from items.models import Item
from accounts.views import sendMail
from django.utils import timezone
from django.core.mail import outbox
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime, timedelta
from unittest.mock import patch
from django.core import mail
import pytz


class LoginViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username='testuser', password='testpassword')

    def test_login_view_success(self):
        response = self.client.post(
            reverse('login'), {'un': 'testuser', 'pa': 'testpassword'})
        self.assertRedirects(response, reverse("home"))

    def test_login_view_failure(self):
        url = reverse('login')
        response = self.client.post(url, {
            'un': 'invaliduser',
            'pa': 'invalidpass'
        })

        # Follow the redirect and check the status code
        redirect_url = response.url
        response = self.client.get(redirect_url)
        self.assertEqual(response.status_code, 200)

        # Check for the error message in the redirected page
        self.assertContains(response, "Invalid Username/Password")


class RegisterViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_view_success(self):
        url = reverse('register')
        response = self.client.post(url, {
            'firstname': 'John',
            'lastname': 'Doe',
            'username': 'johndoe',
            'email': 'johndoe@example.com',
            'p1': 'password',
            'p2': 'password',
            'profile': 'test.jpg',
            'hall': '12',
            'contact': '1234567890'
        })

        # Check if the user and detail objects are created
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Detail.objects.count(), 1)

        # Check if the user is redirected to the login page
        self.assertRedirects(response, reverse('login'))

    def test_register_view_password_mismatch(self):
        url = reverse('register')
        response = self.client.post(url, {
            'firstname': 'John',
            'lastname': 'Doe',
            'username': 'johndoe',
            'email': 'johndoe@example.com',
            'profile': 'test.jpg',
            'hall': '12',
            'p1': 'password',
            'p2': 'wrongpassword',
            'contact': '1234567890'
        })

        # Check if the user is redirected to the register page
        redirect_url = response.url
        response = self.client.get(redirect_url)
        self.assertEqual(response.status_code, 200)

        # Check if the error message is displayed
        self.assertContains(response, "Password does not match")

    def test_register_view_username_exists(self):
        # Create a user with the same username
        User.objects.create_user(
            first_name='Jane', last_name='Doe', email='janedoe@example.com',
            username='johndoe', password='password'
        )

        url = reverse('register')
        response = self.client.post(url, {
            'firstname': 'John',
            'lastname': 'Doe',
            'username': 'johndoe',
            'email': 'johndoe@example.com',
            'p1': 'password',
            'p2': 'password',
            'profile': 'test.jpg',
            'hall': '12',
            'contact': '1234567890'
        })

        # Check if the user is redirected to the register page
        redirect_url = response.url
        response = self.client.get(redirect_url)
        self.assertEqual(response.status_code, 200)

        # Check if the error message is displayed
        self.assertContains(response, "Username Taken")

    def test_register_view_email_exists(self):
        # Create a user with the same email
        User.objects.create_user(
            first_name='Jane', last_name='Doe', email='johndoe@example.com',
            username='janedoe', password='password'
        )

        url = reverse('register')
        response = self.client.post(url, {
            'firstname': 'John',
            'lastname': 'Doe',
            'username': 'johndoe',
            'email': 'johndoe@example.com',
            'p1': 'password',
            'p2': 'password',
            'profile': 'test.jpg',
            'hall': '12',
            'contact': '1234567890'
        })

        # Check if the user is redirected to the register page
        redirect_url = response.url
        response = self.client.get(redirect_url)
        self.assertEqual(response.status_code, 200)

        # Check if the error message is displayed
        self.assertContains(response, "User with this Email already exists")


class LogoutViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass')

    def test_logout(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        self.assertFalse('_auth_user_id' in self.client.session)
        self.assertFalse('_auth_user_backend' in self.client.session)


class AddItemViewTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='testuser@example.com'
        )
        self.client.login(username='testuser', password='testpass123')

    def tearDown(self):
        self.client.logout()
        self.user.delete()

    def test_additem_valid(self):
        # create a valid form data
        form_data = {
            'iname': 'Test Item',
            'img': SimpleUploadedFile('test_image.jpg', b'content'),
            'itag': 'books',
            'disc': 'test product',
            'iprice': 10,
            's_date': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S.%f%z'),
            'e_date': (timezone.localtime() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S.%f%z'),
            'location': 12
        }
        # make a POST request with the form data
        response = self.client.post(
            reverse('additem'), data=form_data, format='multipart')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Item.objects.count(), 1)
        item = Item.objects.first()
        self.assertEqual(item.name, 'Test Item')
        self.assertEqual(item.ownermail, 'testuser@example.com')
        self.assertEqual(item.currentPrice, 10)
        self.assertEqual(item.tag, 'books')

    def test_additem_invalid(self):
        # create an invalid form data with end_date before start_date
        form_data = {
            'iname': 'Test Item',
            'img': SimpleUploadedFile('test_image.jpg', b'content'),
            'itag': 'books',
            'disc': 'test product',
            'iprice': 10,
            's_date': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S.%f%z'),
            'e_date': (timezone.localtime() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S.%f%z'),
            'location': 12
        }
        # make a POST request with the invalid form data
        response = self.client.post(
            reverse('additem'), data=form_data, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)
        self.assertContains(
            response, "Oops!!! Setting of dates was invalid.")


class HomeViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        # self.url = reverse('home')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        self.item1 = Item.objects.create(
            name='TestItem1',
            profile='image.jpg',
            description='This is a test item',
            location=3,
            basePrice=100,
            currentPrice=120,
            minBidPrice=100,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=1),
            highest_bidder=None,
            sendwinmail="notSent",
            tag='nottest',
        )
        self.item2 = Item.objects.create(
            name='TestItem2',
            profile='image2.jpg',
            description='This is another test item',
            location=4,
            basePrice=200,
            currentPrice=320,
            minBidPrice=200,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=1),
            highest_bidder=None,
            sendwinmail="notSent",
            tag='test'
        )

    def test_home_view_with_valid_category(self):
        response = self.client.post(
            reverse('home'), {'category': 'test',  'page': 1})
        self.assertContains(response, 'TestItem2')
        self.assertNotContains(response, 'TestItem1')
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_with_all_categories(self):
        response = self.client.post(
            reverse('home'), {'category': 'All categories',  'page': 1})
        self.assertContains(response, 'TestItem1')
        self.assertContains(response, 'TestItem2')
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_with_future_items(self):
        self.item1.start_date = timezone.now() + timedelta(days=1)
        self.item1.end_date = timezone.now() + timedelta(days=2)
        self.item1.save()
        response = self.client.post(
            reverse('home'), {'category': 'All categories',  'page': 1})
        self.assertContains(response, 'Product : TestItem1')
        self.assertContains(response, 'Base Price: ₹ 100')
        self.assertContains(response, 'Auction Start Date :')
        self.assertTemplateUsed(response, 'home.html')

    @patch('accounts.views.productStatus')
    @patch('accounts.views.sendMail')
    def test_home_view_calls_product_status_and_send_mail(self, mock_send_mail, mock_product_status):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('home'), {'category': 'All categories',  'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_product_status.called)
        self.assertTrue(mock_send_mail.called)

    def tearDown(self):
        self.user.delete()
        self.item1.delete()
        self.item2.delete()


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            first_name='test', last_name='user', email='test@email.com', password='testpass', username='testuser')
        self.user2 = User.objects.create_user(
            first_name='winner', last_name='highest_bidder', email='winner@email.com', password='winnerpass', username='winner')
        self.item = Item.objects.create(
            name='TestItem2',
            profile='image2.jpg',
            description='This is a test item',
            location=4,
            basePrice=200,
            currentPrice=320,
            minBidPrice=200,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=1),
            highest_bidder=2,
            sendwinmail="notSent",
            tag='test'
        )
        self.detail1 = Detail.objects.create(
            username="testuser", contact="1234567890", profile="img", hall=3)
        self.detail2 = Detail.objects.create(
            username="winner", contact="999999999", profile="img2", hall=7)

    def test_dashboard_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('dashboard'))
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

        self.assertContains(response, 'Your Live Auction Products :')
        self.assertContains(response, 'Your Future Auction Products:')
        self.assertContains(response, 'Your Past Auction Products :')
        self.assertContains(response, 'Your Live Bids:')
        self.assertContains(response, 'Your Past Purchases:')

        self.assertContains(response, 'Name : test user')
        self.assertContains(response, 'Username : testuser')
        self.assertContains(response, 'img')
        self.assertContains(response, 'Email-Id : test@email.com')
        self.assertContains(response, 'Contact No : 1234567890')
        self.assertContains(response, 'Hall : 3')

        self.assertContains(response, 'TestItem2')
        self.assertContains(response, 'Current Price : ₹320')
        self.assertContains(response, 'Base Price : ₹200')
        self.assertContains(response, 'Status : unsold')

    def test_dashboard_view_stops_auction_and_sends_emails(self):
        self.client.login(username='testuser', password='testpass')

        response = self.client.post(
            reverse('dashboard'),
            {'item_id': self.item.id}
        )
        self.assertEquals(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEquals(self.item.status, 'past')
        self.assertEquals(self.item.sendwinmail, 'sent')

        # Check if email was sent to the winner
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[0].subject, 'The Dorm Room Dealer')
        self.assertIn(self.item.ownermail, mail.outbox[0].body)
        self.assertIn(str(self.item.ownermail), mail.outbox[0].body)

        # Check if email was sent to the seller
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[1].subject, 'The Dorm Room Dealer')
        self.assertIn(self.user2.email, mail.outbox[1].body)


class SendMailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            first_name='test', last_name='user', email='test@email.com', password='testpass', username='testuser')
        self.user2 = User.objects.create_user(
            first_name='winner', last_name='highest_bidder', email='winner@email.com', password='winnerpass', username='winner')
        self.item = Item.objects.create(
            name='TestItem',
            profile='image.jpg',
            description='This is a test item',
            location=4,
            basePrice=200,
            currentPrice=320,
            minBidPrice=200,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now() - timedelta(days=2),
            end_date=datetime.now() - timedelta(days=1),
            highest_bidder=2,
            sendwinmail="notSent",
            tag='test'
        )
        self.detail1 = Detail.objects.create(
            username="testuser", contact="1234567890", profile="img", hall=3)
        self.detail2 = Detail.objects.create(
            username="winner", contact="999999999", profile="img2", hall=7)

    def test_sends_emails(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            reverse('home'))
        self.assertEquals(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEquals(self.item.status, 'past')
        self.assertEquals(self.item.sendwinmail, 'sent')

        # Check if email was sent to the winner
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[0].subject, 'The Dorm Room Dealer')
        self.assertIn(self.item.ownermail, mail.outbox[0].body)
        self.assertIn(str(self.item.ownermail), mail.outbox[0].body)

        # Check if email was sent to the seller
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[1].subject, 'The Dorm Room Dealer')
        self.assertIn(self.user2.email, mail.outbox[1].body)


class EditProfileTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            first_name='Test',
            last_name='User',
            email='testuser@example.com'
        )
        self.detail = Detail.objects.create(
            username='testuser',
            contact='1234567890',
            profile='image.jpg',
            hall=2
        )
        self.client.login(username='testuser', password='testpass')
        self.url = reverse('edit_profile')

    def test_edit_profile_view_GET(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_profile.html')
        self.assertEqual(response.context['user'].username, 'testuser')
        self.assertEqual(response.context['detail'].contact, '1234567890')
        self.assertEqual(response.context['detail'].hall, 2)

    def test_edit_profile_view_POST(self):
        image_data = SimpleUploadedFile('newimage.jpg', b'content')
        new_data = {
            'firstname': 'New',
            'lastname': 'User',
            'email': 'newuser@example.com',
            'contact': '9876543210',
            'hall': '1',
            'profile': image_data
        }

        response = self.client.post(self.url, data=new_data)
        self.assertRedirects(response, reverse('dashboard'))

        self.user.refresh_from_db()
        self.detail.refresh_from_db()

        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.email, 'newuser@example.com')
        self.assertEqual(self.detail.contact, '9876543210')
        self.assertEqual(self.detail.hall, 1)
        self.assertIn('newimage', self.detail.profile.name)


class BidItemTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.item = Item.objects.create(
            name='TestItem',
            profile='image.jpg',
            description='This is a test item',
            location=4,
            basePrice=200,
            currentPrice=320,
            minBidPrice=200,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now() - timedelta(days=2),
            end_date=datetime.now() - timedelta(days=1),
            highest_bidder=2,
            sendwinmail="notSent",
            tag='test'
        )

    def test_biditem_view_live_item(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('biditem') + '?id=' + str(self.item.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'biditem.html')
        self.assertEqual(response.context['item'], self.item)


class SuccessfullBidTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass', email='test@email.com')
        self.item = Item.objects.create(
            name='TestItem',
            profile='image.jpg',
            description='This is a test item',
            location=4,
            basePrice=100,
            currentPrice=100,
            status='live',
            sold="unsold",
            ownermail="test@email.com",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=1),
            highest_bidder=None,
            sendwinmail="notSent",
            tag='test'
        )

        self.bidder = User.objects.create_user(
            username='bidderuser', password='bidderpass')
        self.bid_value = '110'

    def test_successfull_bid(self):
        self.client.login(username='bidderuser', password='bidderpass')
        url = reverse('successfullBid')
        data = {
            'bidrs': self.bid_value,
            'iid': self.item.id
        }
        bid_value = int(self.bid_value)
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

        # Check that item fields were updated
        item = Item.objects.get(id=self.item.id)
        self.assertEqual(item.currentPrice, bid_value+1)
        self.assertEqual(item.highest_bidder, self.bidder.id)

    #     # Check email was sent to owner of item
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'The Dorm Room Dealer')
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("Your item - ", mail.outbox[0].body)
        self.assertIn(" was bidded by ", mail.outbox[0].body)
        self.assertIn(self.bid_value, mail.outbox[0].body)
        self.assertIn(self.bidder.email, mail.outbox[0].body)

    def test_bid_on_own_item(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('successfullBid')
        data = {
            'bidrs': self.bid_value,
            'iid': self.item.id
        }
        response = self.client.get(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notification.html')
        self.assertEqual(len(mail.outbox), 0)

        # Check that item fields were not updated
        item = Item.objects.get(id=self.item.id)
        self.assertEqual(item.currentPrice, 100)
        self.assertIsNone(item.highest_bidder)


class ProductStatusTestCase(TestCase):
    def setUp(self):
        # create a test user
        self.user = User.objects.create_user(
            username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def test_product_status_live(self):
        # create a test item
        item = Item.objects.create(
            name='Test Item',
            profile='test.jpg',
            img1='test.jpg',
            img2='test.jpg',
            description='Test Description',
            location=1,
            basePrice=100,
            currentPrice=100,
            minBidPrice=100,
            tag='Test Tag',
            status='live',
            sold='unsold',
            ownermail="test@email.com",
            highest_bidder=1,  # highest bidder is assigned
            sendwinmail="notSent",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=1),
        )
        response = self.client.get(reverse('home'))
        item.refresh_from_db()
        self.assertEqual(item.sold, 'Bidded')

    def tearDown(self):
        self.client.logout()


# write a test case for test_product status past


    def test_product_status_past(self):
        # create a test item
        item = Item.objects.create(
            name='Test Item',
            profile='test.jpg',
            img1='test.jpg',
            img2='test.jpg',
            description='Test Description',
            location=1,
            basePrice=100,
            currentPrice=100,
            minBidPrice=100,
            tag='Test Tag',
            status='past',
            sold='Bidded',
            ownermail="test@email.com",
            highest_bidder=1,
            sendwinmail="notSent",
            start_date=datetime.now() - timedelta(days=2),
            end_date=datetime.now() - timedelta(days=1),
        )
        response = self.client.get(reverse('home'))
        item.refresh_from_db()
        self.assertEqual(item.sold, 'Sold')

#     # implement for the product status == future

    def test_product_status_future(self):
        # create a test item
        item = Item.objects.create(
            name='Test Item',
            profile='test.jpg',
            img1='test.jpg',
            img2='test.jpg',
            description='Test Description',
            location=1,
            basePrice=100,
            currentPrice=100,
            minBidPrice=100,
            tag='Test Tag',
            status='future',
            sold='unsold',
            ownermail="test@email.com",
            highest_bidder=None,
            sendwinmail="notSent",
            start_date=datetime.now() + timedelta(days=1),
            end_date=datetime.now() + timedelta(days=2),
        )
        response = self.client.get(reverse('home'))
        item.refresh_from_db()
        self.assertEqual(item.sold, 'Yet to be auctioned')

 # implement for when highest bidder is none and item.status is not from live, past or future

    def test_product_status_none(self):
        # create a test item
        item = Item.objects.create(
            name='Test Item',
            profile='test.jpg',
            img1='test.jpg',
            img2='test.jpg',
            description='Test Description',
            location=1,
            basePrice=100,
            currentPrice=100,
            minBidPrice=100,
            tag='Test Tag',
            status='none',
            sold='unsold',
            ownermail="test@email.com",
            highest_bidder=None,
            sendwinmail="notSent",
            start_date=datetime.now() - timedelta(days=2),
            end_date=datetime.now() - timedelta(days=1),
        )
        response = self.client.get(reverse('home'))
        item.refresh_from_db()
        self.assertEqual(item.sold, 'Unsold')
