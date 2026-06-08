# from rest_framework import serializers

# from ecommerce_backend.users.models import User


# class UserSerializer(serializers.ModelSerializer[User]):
#     class Meta:
#         model = User
#         fields = ["name", "url"]

#         extra_kwargs = {
#             "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
#         }







from rest_framework import serializers

from ecommerce_backend.users.models import User


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "id",
            "email",
            "name",
            "role",
            "phone_number",
            "profile_image",
            "is_active",
            "is_verified",
            "created_at",
            "updated_at",
        ]