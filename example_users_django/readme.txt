Users api documentation

all urls sart with api/users

PublicUser Model:
	username = models.CharField(max_length=128, unique=True)
	profilePic = models.URLField()
	account_creation = models.DateTimeField(auto_now_add=True)
	last_seen_online = models.DateTimeField(null=True)
	friends = models.ManyToManyField('self', symmetrical=False, blank=True)
	single_games_won = models.IntegerField(default=0)
	single_games_lost = models.IntegerField(default=0)
	tournament_games_won = models.IntegerField(default=0)
	tournament_games_lost = models.IntegerField(default=0)
	tournaments_won = models.IntegerField(default=0)
	tournaments_lost = models.IntegerField(default=0)

Url available for frontend :
	'' -> Send back user list. 10 per page. Available qury param : order_by. Available ordering: 
				'username',
				'account_creation',
				'single_games_won',
				'single_games_lost',
				'tournament_games_won',
				'tournament_games_lost',
				'tournaments_won',
				'tournaments_lost',

				available methods : GET. Permission : None.

	'<str:username>/' : Send detail info about one user. Method : Get. Permissions: None
	'<str:username>/friend/' : Send Friend list. Available Method : Get. Permission: User should be authenticated
	'<str:username>/friend/add/<str:friendusername>' : Add a friend to the user. Method: Patch. Permission : User should be authenticated
	'<str:username>/friend/delete/<str:friendusername>' : Delete a friend from user friend list. Method: Delete. Permission: User should be authenticated
	'<str:username>/default_pic/' : Set profile picture to one of the default avatars. Method : Patch Permission : Only owner. ExpectedBody : profile_pic

Url Available for other microservices only:
 	'create/' -> Create a user. Method: Post. Permission: Only Auth
 	'<str:username>/update' -> Update Username. Method: Patch. Permission: Only Auth
 	'delete/<str:username>/' -> Delete User. Method: Patch. Permission: Only Auth
	'<str:username>/increment/<str:lookupfield>/': Increment the given match field by one. Method: Patch. Permission : Only MatchMaking
	'<str:username>/update_pic/': Change path for user profilepic

