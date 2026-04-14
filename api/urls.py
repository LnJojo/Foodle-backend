from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, GroupViewSet, GroupMemberViewSet,
    CompetitionViewSet, RestaurantViewSet, RatingViewSet,
    CustomLoginView, get_csrf_token,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'group-members', GroupMemberViewSet, basename='groupmember')
router.register(r'competitions', CompetitionViewSet, basename='competition')
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'ratings', RatingViewSet, basename='rating')

urlpatterns = [
    path('', include(router.urls)),
    # Login personnalisé pour gérer remember_me
    path('auth/login/', CustomLoginView.as_view(), name='rest_login'),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    # Endpoint pour initialiser le cookie CSRF côté frontend
    path('auth/csrf/', get_csrf_token, name='csrf_token'),
]
