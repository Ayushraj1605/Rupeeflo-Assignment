from rest_framework import serializers


class PassengerInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=0)


class PassengerResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    age = serializers.IntegerField()
    status = serializers.CharField()


class BookingCreateSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()
    passengers = PassengerInputSerializer(many=True)

    def validate_passengers(self, value):
        if not value:
            raise serializers.ValidationError("Passenger list required")
        return value


class BookingResponseSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    status = serializers.CharField()
    passengers = PassengerResponseSerializer(many=True)
    message = serializers.CharField()


class BookingStatusSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()


class BookingDetailSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    status = serializers.CharField()
    schedule_id = serializers.IntegerField()
    passengers = PassengerResponseSerializer(many=True)
    created_at = serializers.DateTimeField()


class BookingListItemSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    status = serializers.CharField()
    schedule_id = serializers.IntegerField()
    passenger_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
