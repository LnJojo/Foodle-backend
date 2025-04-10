from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from users.models import User
from groups.models import Group, GroupFavorite, GroupMember
from competitions.models import Competition, Participant
from restaurants.models import Restaurant, Rating

class UserSerializer(serializers.ModelSerializer):
    class Meta :
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'bio', 'avatar']
        read_only_fields = ['id']
        
    def validate_email(self, value):
        """
        Valide que l'email est unique.
        """
        user = self.context['request'].user if 'request' in self.context else None
        
        # Si c'est une mise à jour, vérifier que l'email est disponible sauf pour l'utilisateur courant
        if self.instance and value == self.instance.email:
            return value
            
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        
        return value

class GroupSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    competition_count = serializers.IntegerField(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator', 'created_at', 'privacy', 'member_count', 'competition_count', 'is_favorite']
        read_only_fields = ['id', 'created_at', 'creator', 'member_count', 'competition_count']

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)
    
    def get_member_count(self, obj):
        """Retourne le nombre de membres du groupe."""
        return obj.members.count()
    
    def get_competition_count(self, obj):
        """Retourne le nombre de compétitions associées au groupe."""
        return obj.competitions.count()
    
    def get_is_favorite(self, obj):
        """Vérifie si le groupe est en favori pour l'utilisateur actuel."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return GroupFavorite.objects.filter(
                user=request.user, 
                group=obj
            ).exists()
        return False
        
    
    # @action(detail=True, methods=['get'])
    # def members(self, request, pk=None):
    #     group = self.get_object()
    #     members = group.members.all()
    #     serializer = UserSerializer(members, many=True)
    #     return Response(serializer.data)

class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'group', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']

    def get_is_current_user(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.user

class RestaurantSerializer(serializers.ModelSerializer):
    suggested_by = UserSerializer(read_only=True)
    average_rating = serializers.ReadOnlyField()
    
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'cuisine_type', 'suggested_by', 
                  'competition', 'visit_date', 'image', 'average_rating', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        # Associer l'utilisateur actuel comme suggérant
        validated_data['suggested_by'] = self.context['request'].user
        return super().create(validated_data)
    
class CompetitionSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    restaurants = RestaurantSerializer(many=True, read_only=True)
    participants = UserSerializer(many=True, read_only=True, source='members')

    class Meta:
        model = Competition
        fields = ['id', 
            'name', 
            'description', 
            'creator', 
            'group', 
            'group_name',
            'start_date', 
            'end_date', 
            'status',
            'participant_count', 
            'created_at',
            'participants',
            'restaurants',]
        read_only_fields = ['id', 'created_at', 'creator', 'participant_count']
    
    def create(self, validated_data):
        # Associer l'utilisateur actuel comme créateur
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)
    
    def get_participant_count(self, obj):
        return obj.participant_count
    
class RatingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    overall_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Rating
        fields = ['id', 'restaurant', 'user', 'food_score', 'service_score', 
                  'ambiance_score', 'value_score', 'comment', 'overall_score', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        # Associer l'utilisateur actuel comme évaluateur
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)