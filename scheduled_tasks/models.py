# scheduled_tasks/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import (models)
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


class BackgroundTaskOutput(models.Model):
    completedtask_id = models.PositiveIntegerField(
        verbose_name="completed task id", default=0, null=False)
    date_output_completed = models.DateTimeField(verbose_name='date output completed', null=True, auto_now=True)
    output_text = models.TextField(blank=True, null=True, verbose_name='background task output')

    class Meta:
        db_table = 'background_task_output'

        def __unicode__(self):
            return 'BackgroundTaskOutput'


class BackgroundTaskOutputManager(models.Model):
    def __str__(self):              # __unicode__ on Python 2
        return "Background Task Output Manager"

    def delete_older_tasks(self, limit_dt):
        success = False
        try:
            BackgroundTaskOutput.objects.filter(date_output_completed__lte=limit_dt).delete()
            success = True
        except Exception as e:
            logger.error("scheduled_tasks_delete_older_tasks threw: " + str(e))

        results = {
            'success':  success,
        }
        return results

    def delete_background_task_output_older_than(self, older_than_date):
        try:
            if positive_value_exists(older_than_date):
                BackgroundTaskOutput.objects.filter(date_output_completed__lte=[older_than_date]).delete()
                status = "DELETE_BACKGROUND_TASK_OUTPUT_SUCCESSFUL"
                success = True
            else:
                status = "DELETE_BACKGROUND_TASK_OUTPUT-MISSING_VARIABLES"
                success = False
        except Exception as e:
            status = "DELETE_BACKGROUND_TASK_OUTPUT-DATABASE_DELETE_EXCEPTION"
            success = False

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    def retrieve_background_task_output_with_completed_id(completedtask_id):
        results = []
        try:
            results = list(BackgroundTaskOutput.objects.filter(completedtask_id__exact=completedtask_id))
        except Exception as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        return results

    def create_output_entry(completedtask_id, date_output_completed, output_text):
        """
        Create an entry that records the results of a scheduled task run.
        Since /PycharmEnvironments/WeVoteServerPy3.7/lib/python3.7/site-packages/background_task/tasks.py @ line 46
        does not send the active task number into the @background task, we have to guess at associating the output to
        the task that was run.  If two tasks complete in the same few seconds, the assumption that the latest task goes
        with the latest output could be wrong.  March 2019
        """
        try:
            completedtask_id_int = convert_to_int(completedtask_id) + 1

            BackgroundTaskOutput.objects.create(
                completedtask_id=completedtask_id_int,
                date_output_completed=date_output_completed,
                output_text=output_text,
            )
            success = True
            status = 'ENTRY_SAVED'
        except Exception:
            success = False
            status = 'SOME_ERROR'

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results
