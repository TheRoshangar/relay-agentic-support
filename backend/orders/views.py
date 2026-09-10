
from django.shortcuts import get_object_or_404

from .models import Order
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import OrderSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def orders_api(request):
    orders = Order.objects.filter(user=request.user)

    serializer = OrderSerializer(orders, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail_api(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    serializer = OrderSerializer(order)

    return Response(serializer.data)

