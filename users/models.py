from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Modèle utilisateur étendu avec des champs supplémentaires"""
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.username