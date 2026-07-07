from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Profile

class TestDBView(APIView):

    def get(self, request):
        # Check if the database is reachable by trying to fetch a user
        try:
            user = Profile.objects.first()
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)
        if user is None:
            return Response({"status": "ok", "message": "No users found in the database"}, status=200)
        return Response({"id": user.id, "username": user.username, "email": user.email}, status=200)


    def post(self, request):
        # Get the data from the request
        data = request.data

        # Validate the data
        if "username" not in data or "email" not in data:
            return Response({"error": "Missing required fields"}, status=400)

        # Create a new user
        user = Profile.objects.create(
            username=data["username"],
            email=data["email"],
            password=data.get("password", None)
        )

        # Return the created user
        return Response({"id": user.id, "username": user.username, "email": user.email}, status=201)
    
# {"username":"cedric", "email":"cedric@hypertube.net", "password":"testcedric"}