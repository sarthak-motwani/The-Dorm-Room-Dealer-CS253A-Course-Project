from django.test import SimpleTestCase
from django.urls import reverse, resolve
from accounts.views import login, register, home, logout, dashboard, edit_profile


class TestUrls(SimpleTestCase):

    def test_login_url_is_resolved(self):
        url = reverse("login")
        print(resolve(url))
        self.assertEquals(resolve(url).func, login)

    def test_register_url_is_resolved(self):
        url = reverse("register")
        print(resolve(url))
        self.assertEquals(resolve(url).func, register)

    def test_home_url_is_resolved(self):
        url = reverse("home")
        print(resolve(url))
        self.assertEquals(resolve(url).func, home)

    def test_logout_url_is_resolved(self):
        url = reverse("logout")
        print(resolve(url))
        self.assertEquals(resolve(url).func, logout)

    def test_dashboard_url_is_resolved(self):
        url = reverse("dashboard")
        print(resolve(url))
        self.assertEquals(resolve(url).func, dashboard)

    def test_edit_profile_url_is_resolved(self):
        url = reverse("edit_profile")
        print(resolve(url))
        self.assertEquals(resolve(url).func, edit_profile)
