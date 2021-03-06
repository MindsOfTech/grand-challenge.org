from rest_framework import serializers

from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class ComponentInterfaceSerialzer(serializers.ModelSerializer):
    kind = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ComponentInterface
        fields = [
            "title",
            "description",
            "slug",
            "kind",
            "pk",
        ]
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            kind=model._meta.get_field("kind")
        )


class ComponentInterfaceValueSerializer(serializers.ModelSerializer):
    image = serializers.HyperlinkedRelatedField(
        queryset=Image.objects.all(), view_name="api:image-detail",
    )
    interface = ComponentInterfaceSerialzer()

    class Meta:
        model = ComponentInterfaceValue
        fields = [
            "interface",
            "value",
            "file",
            "image",
            "pk",
        ]
