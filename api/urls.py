from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, GroupViewSet, GroupMemberViewSet,
    CompetitionViewSet, RestaurantViewSet, RatingViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'group-members', GroupMemberViewSet, basename='groupmember')
router.register(r'competitions', CompetitionViewSet, basename='competition')
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'ratings', RatingViewSet, basename='rating')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
]
