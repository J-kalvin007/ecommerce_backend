
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from .models import User
from dj_rest_auth.serializers import LoginSerializer


class CustomRegisterSerializer(RegisterSerializer):
    name = serializers.CharField(
        max_length=100,
        required=True
    )

    def get_cleaned_data(self):
        data = super().get_cleaned_data()

        data["name"] = self.validated_data.get("name", "")

        return data

    def save(self, request):
        user = super().save(request)

        user.name = self.validated_data["name"]

        user.save(update_fields=["name"])

        return user






class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "name",
            "role",
            "phone_number",
            "profile_image",
            "is_active",
            "is_verified",
        )




class CustomLoginSerializer(LoginSerializer):
    pass