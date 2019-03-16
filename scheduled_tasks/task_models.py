# scheduled_tasks/task_models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import logging
from django.utils import timezone
from background_task.models import Task

from wevote_functions.functions import positive_value_exists


logger = logging.getLogger(__name__)


class WeTask(Task):

    def raw_list(self):
        now = timezone.now()

        return list(Task.objects.unlocked(now).order_by('id'))

    def delete_task (self, id):
        try:
            if positive_value_exists(id):
                Task.objects.filter(id=id).delete()
                status = "DELETE_TASK_SUCCESSFUL"
                success = True
            else:
                status = "DELETE_TASK-MISSING_ID"
                success = False
        except Exception as e:
            status = "DELETE_TASK-DATABASE_DELETE_EXCEPTION"
            success = False

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    class Meta:
        app_label = 'WeVoteServer'
