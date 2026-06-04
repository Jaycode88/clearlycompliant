from django.db import models
from orders.models import Order


class Report(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='report')
    pdf = models.BinaryField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.order.domain}"