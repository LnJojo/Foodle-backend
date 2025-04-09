from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Restaurant(models.Model):
    """Modèle pour un restaurant proposé dans une compétition"""
    name = models.CharField(max_length=100)
    address = models.TextField()
    cuisine_type = models.CharField(max_length=50)

    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='suggested_restaurants'
        )
    competition = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.CASCADE,
        related_name='restaurants' 
        )
    
    visit_date = models.DateField()

    image = models.ImageField(
        upload_to='restaurants/',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @property
    def average_rating(self):
        """Calcule la note moyenne du restaurant"""
        ratings = self.ratings.all()  # Récupère toutes les évaluations (via related_name de Rating)
        if not ratings:
            return 0
        total = sum(rating.overall_score for rating in ratings)
        return round(total / len(ratings), 1)
    
class Rating(models.Model):
    """Modèle pour une évaluation d'un restaurant par un participant"""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    food_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    service_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    ambiance_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    value_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('restaurant', 'user')
        
    def __str__(self):
        return f"Évaluation de {self.restaurant.name} par {self.user.username}"
    
    @property
    def overall_score(self):
        """Calcule la note globale"""
        return round((self.food_score + self.service_score + 
                     self.ambiance_score + self.value_score) / 4, 1)

