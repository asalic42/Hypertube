from datetime import timedelta
from rest_framework import serializers
from .models import PublicUser
from django.utils.timezone import now

class PublicUserDetailSerializer(serializers.ModelSerializer):
    total_tournaments_pong = serializers.SerializerMethodField()
    total_tournaments_c4 = serializers.SerializerMethodField()
    total_single_games_pong = serializers.SerializerMethodField()
    total_single_games_c4 = serializers.SerializerMethodField()
    tournament_pong_win_rate = serializers.SerializerMethodField()
    tournament_c4_win_rate = serializers.SerializerMethodField()
    single_games_pong_win_rate = serializers.SerializerMethodField()
    single_games_c4_win_rate = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    is_your_friend = serializers.SerializerMethodField()
    friend_management = serializers.SerializerMethodField()
    c4_matches = serializers.SerializerMethodField()
    pong_matches = serializers.SerializerMethodField()
    c4_tournaments = serializers.SerializerMethodField()
    pong_tournaments = serializers.SerializerMethodField()
    class Meta:
        model = PublicUser
        fields =  ['username','profilePic', 'account_creation', 'is_online',
                   'single_games_pong_won', 'single_games_pong_lost',
                   'single_games_c4_won', 'single_games_c4_lost',
                   'tournaments_pong_won', 'tournaments_pong_lost',
                   'tournaments_c4_won', 'tournaments_c4_lost',
                   'total_tournaments_pong', 'total_tournaments_c4',
                   'total_single_games_pong', 'total_single_games_c4',
                   'tournament_pong_win_rate', 'tournament_c4_win_rate',
                   'single_games_pong_win_rate', 'single_games_c4_win_rate',
                   'is_your_friend', 'friend_management', 'c4_matches',
                   'pong_matches', 'c4_tournaments', 'pong_tournaments',
                  ]
        
        
    def get_c4_matches(self, obj):
        return(f'/api/history/match/?username={obj.username}&game_type=c4')

    def get_pong_matches(self, obj):
        return(f'/api/history/match/?username={obj.username}&game_type=pong')

    def get_c4_tournaments(self, obj):
        return(f'/api/history/tournament/?username={obj.username}&game_type=c4')

    def get_pong_tournaments(self, obj):
        return(f'/api/history/tournament/?username={obj.username}&game_type=pong')

    def get_total_tournaments_pong(self, obj):
        return obj.tournaments_pong_won + obj.tournaments_pong_lost


    def get_total_tournaments_c4(self, obj):
        return obj.tournaments_c4_won + obj.tournaments_c4_lost


    def get_total_single_games_pong(self, obj):
        return obj.single_games_pong_won + obj.single_games_pong_lost
    
    
    def get_total_single_games_c4(self, obj):
        return obj.single_games_c4_won + obj.single_games_c4_lost


    def get_tournament_pong_win_rate(self, obj):
        total_tournament_pong = self.get_total_tournaments_pong(obj)
        return obj.tournaments_pong_won / total_tournament_pong if total_tournament_pong != 0 else 0


    def get_tournament_c4_win_rate(self, obj):
        total_tournament_c4 = self.get_total_tournaments_c4(obj)
        return obj.tournaments_c4_won / total_tournament_c4 if total_tournament_c4 != 0 else 0


    def get_single_games_pong_win_rate(self, obj):
        total_games_pong = self.get_total_single_games_pong(obj)
        return obj.single_games_pong_won / total_games_pong if total_games_pong != 0 else 0


    def get_single_games_c4_win_rate(self, obj):
        total_games_c4 = self.get_total_single_games_c4(obj)
        return obj.single_games_c4_won / total_games_c4 if total_games_c4 != 0 else 0


    def get_is_online(self, obj):
        if obj.last_seen_online == None or now() - obj.last_seen_online > timedelta(minutes=15):
            return False 
        return True


    def get_is_your_friend(self, obj):
        request = self.context.get('request')
        if request.user is not None:
            if obj.id == request.user.id:
                return None
            try:
                user = PublicUser.objects.get(pk=request.user.id)
            except PublicUser.DoesNotExist:
                return None
            if user.friends.filter(id=obj.pk).exists():
                return True
            return False
        else :
            return None


    def get_friend_management(self, obj):
        request = self.context.get('request')
        if request.user is not None and request.user.id != obj.id:
            try:
                logged_user = PublicUser.objects.get(pk=request.user.id)
            except PublicUser.DoesNotExist:
                return None

            if logged_user.friends.filter(id=obj.pk).exists():
                return {
                    'action': 'remove',
                    'url': f'/api/users/{logged_user.username}/friends/delete/{obj.username}/'
                }
            else:
                return {
                    'action': 'add',
                    'url': f'/api/users/{logged_user.username}/friends/add/{obj.username}/'
                }
        return None


class PublicUserListSerializer(serializers.ModelSerializer):
    is_your_friend = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    full_profile = serializers.HyperlinkedIdentityField(
            view_name='user-detail',
            lookup_field='username'
            )
    friend_management = serializers.SerializerMethodField()
    class Meta:
        model = PublicUser
        fields = ['username', 'profilePic', 'is_online', 'full_profile', 'is_your_friend', 'friend_management']

    def get_is_online(self, obj): 
        if obj.last_seen_online == None or now() - obj.last_seen_online > timedelta(minutes=5):
            return False 
        return True
    
    def get_is_your_friend(self, obj):
        request = self.context.get('request')
        if request.user is not None:
            if obj.id == request.user.id:
                return None
            try:
                user = PublicUser.objects.get(pk=request.user.id)
            except PublicUser.DoesNotExist:
                return None
            if user.friends.filter(id=obj.pk).exists():
                return True
            return False
        else :
            return None

    def get_friend_management(self, obj):
        request = self.context.get('request')
        if request.user is not None and request.user.id != obj.id:
            try:
                logged_user = PublicUser.objects.get(pk=request.user.id)
            except PublicUser.DoesNotExist:
                return None

            if logged_user.friends.filter(id=obj.pk).exists():
                return {
                    'action': 'remove',
                    'url': f'/api/users/{logged_user.username}/friends/delete/{obj.username}/'
                }
            else:
                return {
                    'action': 'add',
                    'url': f'/api/users/{logged_user.username}/friends/add/{obj.username}/'
                }
        return None
