from datetime import datetime, timedelta
from rest_framework import viewsets, permissions, filters
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from dj_rest_auth.views import LoginView as DjLoginView
from django.conf import settings as django_settings


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Endpoint public qui force Django à émettre le cookie CSRF.
    Appelé une fois au chargement de l'app pour que les futures requêtes
    authentifiées puissent inclure le header X-CSRFToken.
    """
    return JsonResponse({'detail': 'ok'})


class CustomLoginView(DjLoginView):
    """
    Étend la vue de login pour supporter le paramètre remember_me.
    Sans remember_me=true, les cookies JWT deviennent des cookies de session
    (supprimés à la fermeture du navigateur).
    Avec remember_me=true, les cookies ont une expiration explicite de 30 jours.
    """
    def get_response(self):
        response = super().get_response()
        remember_me = self.request.data.get('remember_me', False)

        if not remember_me:
            # Supprimer expires et max-age pour transformer en cookies de session
            for cookie_key in [
                django_settings.REST_AUTH.get('JWT_AUTH_COOKIE'),
                django_settings.REST_AUTH.get('JWT_AUTH_REFRESH_COOKIE'),
            ]:
                if cookie_key and cookie_key in response.cookies:
                    response.cookies[cookie_key]['expires'] = ''
                    response.cookies[cookie_key]['max-age'] = ''

        return response

from .serializers import (
    UserSerializer, GroupSerializer, GroupMemberSerializer,
    CompetitionSerializer, RestaurantSerializer, RatingSerializer
)

from users.models import User
from groups.models import Group, GroupInvitation, GroupMember, GroupFavorite
from competitions.models import Competition, Participant
from restaurants.models import Restaurant, Rating

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_queryset(self):
        # Limite la visibilité aux utilisateurs partageant au moins un groupe avec l'utilisateur connecté
        user = self.request.user
        group_ids = GroupMember.objects.filter(user=user).values_list('group_id', flat=True)
        return User.objects.filter(custom_groups__in=group_ids).distinct()

class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'description']
    filterset_fields = ['creator']
    
    def get_queryset(self):
        queryset = Group.objects.filter(
            members=self.request.user
        )
        
        # Pour le débogage - imprimez le nombre réel de membres pour chaque groupe
        for group in queryset:
            actual_members = GroupMember.objects.filter(group=group).count()
            print(f"Group '{group.name}' (ID: {group.id}) has {actual_members} actual members")
        
        # Maintenant continuez avec les annotations
        queryset = queryset.annotate(
            member_count=Count('membership', distinct=True),
            competition_count=Count('competitions', distinct=True)
        ).prefetch_related('members', 'competitions')
        
        # Vérifiez le résultat après annotation
        for group in queryset:
            print(f"After annotation, Group '{group.name}' has member_count: {group.member_count}")
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        group = self.get_object()
        members = GroupMember.objects.filter(group=group).select_related('user')
        serializer = GroupMemberSerializer(
            members, 
            many=True,
            context={'request': request} 
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_group(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Crée le groupe et ajoute le créateur comme membre admin
        group = serializer.save(creator=request.user)
        GroupMember.objects.create(
            group=group,
            user=request.user,
            role='admin'
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def create_invitation(self, request, pk=None):
        """Crée un lien d'invitation pour le groupe"""
        group = self.get_object()
        user = request.user
        
        # La correction est ici - il faut utiliser le modèle GroupMember pour vérifier le rôle
        # Au lieu de group.members.filter(user=user, role='admin').exists():
        if not GroupMember.objects.filter(group=group, user=user, role='admin').exists():
            return Response(
                {"detail": "Seuls les administrateurs peuvent créer des invitations."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Optionnel : définir une date d'expiration (ex: 7 jours)
        expires_at = timezone.now() + timedelta(days=7)
        
        invitation = GroupInvitation.objects.create(
            group=group,
            created_by=user,
            expires_at=expires_at
        )
        
        return Response({
        "id": str(invitation.id),  # Convertir UUID en chaîne
        "expires_at": expires_at
    })

    @action(detail=False, methods=['get'], url_path='invitations/(?P<invitation_id>[^/.]+)')
    def verify_invitation(self, request, invitation_id=None):
        """Vérifie si une invitation est valide et renvoie les informations du groupe"""
        try:
            invitation = GroupInvitation.objects.get(id=invitation_id, is_active=True)
            
            # Vérifier si l'invitation a expiré - utilisez timezone.now() au lieu de datetime.now()
            if invitation.expires_at and invitation.expires_at < timezone.now():
                invitation.is_active = False
                invitation.save()
                return Response(
                    {"detail": "Ce lien d'invitation a expiré."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            group = invitation.group
            
            # Vérifier si l'utilisateur est déjà membre
            is_already_member = GroupMember.objects.filter(
                group=group, 
                user=request.user
            ).exists()
            
            return Response({
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description
                },
                "is_already_member": is_already_member
            })
            
        except GroupInvitation.DoesNotExist:
            return Response(
                {"detail": "Lien d'invitation invalide ou expiré."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], url_path='join/(?P<invitation_id>[^/.]+)')
    def join_with_invitation(self, request, invitation_id=None):
        """Permet à l'utilisateur de rejoindre un groupe via un lien d'invitation"""
        try:
            invitation = GroupInvitation.objects.get(id=invitation_id, is_active=True)
            
            # Vérifier si l'invitation a expiré 
            if invitation.expires_at and invitation.expires_at < timezone.now():
                invitation.is_active = False
                invitation.save()
                return Response(
                    {"detail": "Ce lien d'invitation a expiré."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            group = invitation.group
            user = request.user
            
            # Vérifier si l'utilisateur est déjà membre
            if GroupMember.objects.filter(group=group, user=user).exists():
                return Response({
                    "detail": "Vous êtes déjà membre de ce groupe.",
                    "group": {
                        "id": group.id,
                        "name": group.name
                    }
                })
            
            # Ajouter l'utilisateur comme membre
            GroupMember.objects.create(
                user=user,
                group=group,
                role='member'
            )

            updated_group = Group.objects.filter(id=group.id).annotate(
                member_count=Count('membership', distinct=True),
                competition_count=Count('competitions', distinct=True)
            ).first()
            
            return Response({
                "detail": "Vous avez rejoint le groupe avec succès.",
                "group": {
                    "id": group.id,
                    "name": group.name
                }
            })
            
        except GroupInvitation.DoesNotExist:
            return Response(
                {"detail": "Lien d'invitation invalide ou expiré."},
                status=status.HTTP_404_NOT_FOUND
            )
        
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Ajoute ou retire un groupe des favoris de l'utilisateur."""
        group = self.get_object()
        user = request.user
        
        # Vérifie si le groupe est déjà en favori
        favorite_exists = GroupFavorite.objects.filter(
            user=user, 
            group=group
        ).exists()
        
        if favorite_exists:
            # Si oui, on le supprime
            GroupFavorite.objects.filter(user=user, group=group).delete()
            return Response({"status": "removed", "message": "Groupe retiré des favoris"})
        else:
            # Sinon, on l'ajoute
            GroupFavorite.objects.create(user=user, group=group)
            return Response({"status": "added", "message": "Groupe ajouté aux favoris"})
    
class GroupMemberViewSet(viewsets.ModelViewSet):
    serializer_class = GroupMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'user', 'role']

    def get_queryset(self):
        user = self.request.user
        return GroupMember.objects.filter(group__members=user)

    def _is_group_admin(self, group):
        """Vérifie si l'utilisateur connecté est admin du groupe."""
        return GroupMember.objects.filter(
            group=group, user=self.request.user, role='admin'
        ).exists()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._is_group_admin(instance.group):
            return Response(
                {"detail": "Seuls les administrateurs peuvent modifier les membres."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Un membre peut se retirer lui-même, sinon il faut être admin
        if instance.user != request.user and not self._is_group_admin(instance.group):
            return Response(
                {"detail": "Seuls les administrateurs peuvent retirer des membres."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
class CompetitionViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'description']
    filterset_fields = ['group', 'creator', 'status']
    
    def get_queryset(self):
        return Competition.objects.filter(
            group__members=self.request.user
        ).select_related(
            'creator', 'group'
        ).prefetch_related(
            'members','restaurants'  # Important pour compter les participants
        ).annotate(
            participant_count=Count('members')
        ).distinct()
    
    @action(detail=False, methods=['post'])
    def create_competition(self, request):
        serializer = CompetitionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Assigner automatiquement l'utilisateur actuel comme créateur
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Retourne la liste des participants d'une compétition spécifique"""
        competition = self.get_object()
        participants = competition.members.all()  # Utilisez le nom de la relation dans votre modèle
        serializer = UserSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Permet à l'utilisateur authentifié de rejoindre une compétition"""
        competition = self.get_object()
        user = request.user
        
        # Vérifier si l'utilisateur est déjà un participant
        if competition.members.filter(id=user.id).exists():
            return Response(
                {"detail": "Vous êtes déjà un participant de cette compétition."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ajouter l'utilisateur comme participant
        Participant.objects.create(
            user=user,
            competition=competition
        )
        
        return Response(
            {"detail": "Vous avez rejoint la compétition avec succès."},
            status=status.HTTP_201_CREATED
        )
    
class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'address', 'cuisine_type']
    filterset_fields = ['competition', 'suggested_by']
    
    def get_queryset(self):
        # Récupérer les restaurants des compétitions des groupes dont l'utilisateur est membre
        user = self.request.user
        return Restaurant.objects.filter(competition__group__members=user)

class RatingViewSet(viewsets.ModelViewSet):
    serializer_class = RatingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurant', 'user']
    
    def get_queryset(self):
        user = self.request.user
        # Filtre toujours par appartenance au groupe, même quand restaurant_id est fourni
        queryset = Rating.objects.filter(restaurant__competition__group__members=user)
        restaurant_id = self.request.query_params.get('restaurant', None)
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset



