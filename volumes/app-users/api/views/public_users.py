from rest_framework.views import APIView, Response
from api.models import PublicUser

class PublicUserList(APIView):
    """ retrieve a list of all users from the database """
    def get(self, request):
        users = PublicUser.objects.all()
        return Response({"users": list(users.values())})

class PublicUserCreate(APIView):
    """ create a new user in the database """
    def post(self, request):
        user = PublicUser.objects.create(**request.data)
        return Response({"message": "User created successfully"})

class PublicUserRetrieveDetail(APIView):
    """ retrieve a specific user from the database """
    def get(self, request, username):
        user = PublicUser.objects.get(username=username)
        return Response({"message": "User retrieved successfully", "user": {
            "username": user.username,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "email": user.email,
            "profilePic": user.profilePic,
            "preferredLanguage": user.preferredLanguage
        }})

class PublicUserUpdate(APIView):
    """ update a specific user in the database """
    def patch(self, request, username):
        user = PublicUser.objects.get(username=username)
        for key, value in request.data.items():
            setattr(user, key, value)
        user.save()
        return Response({"message": "User updated successfully"})

class PublicUserUpdateAvatar(APIView):
    """ update a specific user's avatar in the database """
    def patch(self, request, username):
        user = PublicUser.objects.get(username=username)
        user.profilePic = request.data.get("profilePic", user.profilePic)
        user.save()
        return Response({"message": "User avatar updated successfully"})

class PublicUserDelete(APIView):
    """ delete a specific user from the database """
    def delete(self, request, username):
        user = PublicUser.objects.get(username=username)
        user.delete()
        return Response({"message": "User deleted successfully"})
