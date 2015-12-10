# star/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import StarItem
from .serializers import StarItemSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportStarItemDataView(APIView):
    def get(self, request, format=None):
        star_list = StarItem.objects.all()
        serializer = StarItemSerializer(star_list, many=True)
        return Response(serializer.data)
