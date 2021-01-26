from rest_framework import status
from .serilizers import UserSerializer
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base_app.models import UserProfile


class MyTokenObtainSerilizer(TokenObtainPairSerializer):
    # serializer_class = TokenObtainPairSerializer
    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        # Add your required response and other parameters here
        data['username'] = self.user.username
        data['message'] = "login successful"

        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainSerilizer


class UserView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        post_data = dict(request.data)
        user_name = User.objects.filter(username=post_data['username'])
        if user_name.exists():
            return Response({"response": "username already taken"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        email = User.objects.filter(email=post_data['email'])
        if email.exists():
            return Response({"response": "email already exists"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        if post_data['password1'] != post_data['password2']:
            return Response({"response": "Passwords don't match"}, status=status.HTTP_406_NOT_ACCEPTABLE)

        user = User.objects.create_user(
            username=post_data['username'],
            email=post_data['email'],
            password=post_data['password1']
        )
        # Additional Information Other Than Built User Model Attributes
        userprofile = UserProfile()
        userprofile.user = user
        userprofile.address = post_data['address']
        userprofile.age = post_data['age']
        userprofile.save()

        new_user = {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
        user.set_password(post_data['password1'])
        user.save()
        return Response(new_user, status=status.HTTP_201_CREATED)

    def get(self, request):
        # print(request.headers['Authorization'])
        user_data = User.objects.all()
        serializer = UserSerializer(user_data, many=True)
        data = [{"id": dict(d)['id'],
                 "username": dict(d)['username'],
                 "email": dict(d)['email']} for d in serializer.data
                ]
        return Response(data, status=status.HTTP_200_OK)


class UserDetail(APIView):
    def get_user_not_found_response(self):
        return {"response": {"response": "user does not exist"}, "status": status.HTTP_400_BAD_REQUEST}

    def is_user_found(self, pk):
        return User.objects.filter(pk=pk).exists()

    def get_response(self, pk):
        user_data = User.objects.get(pk=pk)
        serilizer = UserSerializer(user_data)
        response = {
            "id": serilizer.data['id'],
            "username": serilizer.data['username'],
            'email': serilizer.data['email'],
            "address": user_data.userprofile.address,
            "age": user_data.userprofile.age
        }
        return response

    def get(self, request, pk):
        has_user = self.is_user_found(pk)
        if has_user:
            user_data = self.get_response(pk)
            return Response(user_data, status=status.HTTP_200_OK)
        else:
            response = self.get_user_not_found_response()
            return Response(response['response'], status=response['status'])

    def put(self, request, pk):
        has_user = self.is_user_found(pk)
        if has_user:
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user, data=request.data)
            if serializer.is_valid():
                current_email = user.email
                updated_email = request.data['email']
                email_data = User.objects.filter(email=updated_email)
                conditions = [
                    current_email != updated_email,
                    len(email_data) > 0
                ]
                if all(conditions):
                    return Response({"response": "email already exists"})
                serializer.save()
                user.set_password(serializer.data['password1'])
                user.save()
                userprofile = UserProfile.objects.get(user=user)
                userprofile.age = request.data['age']
                userprofile.address = request.data['address']
                userprofile.save()
                user_data = self.get_response(pk)
                return Response(user_data)
            else:
                return Response({"response": "username already taken"})
        else:
            response = self.get_user_not_found_response()
            return Response(response['response'], status=response['status'])

    def delete(self, request, pk):
        has_user = self.is_user_found(pk)
        if has_user:
            user = User.objects.get(pk=pk)
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            response = self.get_user_not_found_response()
            return Response(response['response'], status=response['status'])
