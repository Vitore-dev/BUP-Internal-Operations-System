from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('HR', 'HR'),
        ('FINANCE', 'Finance'),
        #('RECEPTION', 'Reception'),
        ('DIRECTOR', 'Director'),
        #('OPS_MANAGER', 'Operations Manager'),
        ('PI', 'Project Coordinator'),
    ]

    azure_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"