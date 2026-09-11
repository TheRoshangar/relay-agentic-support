from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def login_api(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username and password are required"},
            status=400,
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {"error": "Invalid username or password"},
            status=401,
        )

    login(request, user)

    return Response({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
        }
    })


@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def csrf_token_api(request):
    return Response({
        "csrfToken": get_token(request)
    })

