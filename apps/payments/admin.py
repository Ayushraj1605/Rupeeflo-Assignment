from django.contrib import admin
from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "razorpay_payment_id", "amount_paise", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("razorpay_payment_id", "razorpay_order_id")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "razorpay_refund_id", "amount_paise", "status", "reason", "created_at")
    list_filter = ("status",)
    search_fields = ("razorpay_refund_id",)
