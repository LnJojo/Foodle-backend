import uuid
from django.db import models
from django.conf import settings

class Group(models.Model):
    """Modèle pour un groupe d'amis qui organisent des compétitions"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups',
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='GroupMember',
        related_name='custom_groups',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    PRIVACY_CHOICES = [
        ('private', 'Privé - Sur invitation uniquement'),
        ('public', 'Public - Ouvert à tous'),
    ]
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')

    def __str__(self):
        return self.name
    
    def get_member_count(self):
        return self.membership.count()


class GroupMember(models.Model):
    """Modèle liant un utilisateur à un groupe"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
        )
    group = models.ForeignKey(
        Group, 
        on_delete=models.CASCADE,
        related_name='membership',
        )
    
    joined_at = models.DateTimeField(auto_now_add=True)

    ROLE_CHOICES = [
        ('member', 'Membre'),
        ('admin', 'Administrateur'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"
    
class GroupInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey('Group', on_delete=models.CASCADE, related_name='invitations')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Optionnel : expiration du lien
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Invitation to {self.group.name} by {self.created_by.username}"
    
class GroupFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_groups'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')  # Un utilisateur ne peut mettre un groupe en favori qu'une seule fois
        
    def __str__(self):
        return f"{self.user.username} - {self.group.name} (favori)"
