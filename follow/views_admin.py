# follow/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FollowOrganization
from .serializers import FollowOrganizationSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportFollowOrganizationDataView(APIView):
    def get(self, request, format=None):
        follow_organization_list = FollowOrganization.objects.all()
        serializer = FollowOrganizationSerializer(follow_organization_list, many=True)
        return Response(serializer.data)
