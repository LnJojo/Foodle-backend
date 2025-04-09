from django.db import models
from django.conf import settings

class Competition(models.Model):
    """Modèle pour une compétition de restaurants entre amis"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, 
                                on_delete=models.CASCADE, 
                                related_name='created_competition')
    
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='competitions'
    )

    members = models.ManyToManyField(  # Changé de 'participants' à 'members'
        settings.AUTH_USER_MODEL,
        through='Participant',
        related_name='competitions_participated',  # Nom de relation inverse
        blank=True
    )
    
    start_date = models.DateField()
    end_date = models.DateField()

    STATUS_CHOICES = [
        ('planning', 'En préparation'),
        ('active', 'En cours'),
        ('completed', 'Terminée'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='planning'
    )

    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
    

class Participant(models.Model):
    """Modèle liant un utilisateur à une compétition"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'competition')
        
    def __str__(self):
        return f"{self.user.username} - {self.competition.name}"