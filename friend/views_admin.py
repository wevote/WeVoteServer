# friend/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchDescription, BatchHeaderMap, BatchManager, BatchRow
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import MEASURE, OFFICE, CANDIDATE
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import urlquote
from election.models import Election, ElectionManager
from position.models import POSITION
from voter.models import voter_has_authority
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

