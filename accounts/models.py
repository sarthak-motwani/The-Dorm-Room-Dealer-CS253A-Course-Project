from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission

# Create your models here.

class Detail(models.Model):
    username = models.CharField(max_length=50)
    contact = models.CharField(max_length=10)
    profile = models.ImageField(upload_to='pics',null=True )
    hall = models.IntegerField(null=True)

class Notification(models.Model):
    message = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    # add a bool field to check if Notification has been seen
    seen = models.BooleanField(default=False)

    def __str__(self):
        return self.message
class CustomUser(AbstractUser):
    notifications = models.ManyToManyField(Notification, blank=True, related_name='users_notifications')
    groups = models.ManyToManyField(Group, blank=True, related_name='users_groups')
    user_permissions = models.ManyToManyField(Permission, blank=True, related_name='users_permissions')

    def __str__(self):
        return self.username
    # function to append notifications
    def add_notification(self, message):
        self.notifications.create(message=message)
    # function to remove notifications


    
