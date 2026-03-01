from rest_framework import serializers


class CreatePaymentOrderResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    key_id = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField()


class VerifyPaymentRequestSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    payment_id = serializers.CharField()
    signature = serializers.CharField()


class PaymentStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class RefundRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="cancellation", max_length=255)


class RefundResponseSerializer(serializers.Serializer):
    refund_id = serializers.CharField()
    razorpay_refund_id = serializers.CharField()
    amount_paise = serializers.IntegerField()
    status = serializers.CharField()
    reason = serializers.CharField()
    message = serializers.CharField()
