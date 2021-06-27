from datetime import time
from logging import error
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone

from measure.models import ContestMeasure
from position.models import PositionEntered

import json

class WeVoteAPIsV1TestsPositionListForBallotItem(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.position_list_for_ballot_item_url = reverse("apis_v1:positionListForBallotItemView")
