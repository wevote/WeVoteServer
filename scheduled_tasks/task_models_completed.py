# scheduled_tasks/task_models_completed.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import logging
from background_task.models import CompletedTask  # DALE 2020-01-17 To prevent ModuleNotFoundError


logger = logging.getLogger(__name__)


class WeTaskCompleted(CompletedTask):

    def raw_list(self, limit=25):
        return list(CompletedTask.objects.order_by('-id')[:limit])

    def delete_older_tasks(self, limit_dt):
        success = False
        try:
            CompletedTask.objects.filter(run_at__lte=limit_dt).delete()
            success = True
        except Exception as e:
            logger.error("completed_tasks_delete_older_tasks threw: " + str(e))

        results = {
            'success':  success,
        }
        return results

    class Meta:
        app_label = 'WeVoteServer'
