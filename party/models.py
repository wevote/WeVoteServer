# party/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
import wevote_functions.admin
from wevote_settings.models import fetch_next_we_vote_id_party_integer, fetch_site_unique_id_prefix
from exception.models import handle_record_not_found_exception

logger = wevote_functions.admin.get_logger(__name__)


class Party(models.Model):
    # The unique ID of this Party. (Provided by CTCL).
    # TODO party_ctcl_id_temp is unique for each data file, however it may not be unique across different data feeds
    party_id_temp = models.CharField(verbose_name="temporary party id", max_length=255, null=True, unique=True)
    we_vote_id = models.CharField(verbose_name="party we_vote_id", max_length=32, null=True, unique=True)
    # Make unique=True after data is migrated
    party_name = models.CharField(verbose_name="party name", max_length=255, null=False, unique=False)
    party_abbreviation = models.CharField(verbose_name="party abbreviation", max_length=255, null=True, unique=False,
                                          blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", null=True, blank=True, max_length=255, unique=True)

    # TRUE = 'True'
    # FALSE = 'False'
    # PARTY_ISWRITE_IN_CHOICES = (
    #     (TRUE, 'True'),
    #     (FALSE, 'False')
    # )
    # party_color = models.CharField(verbose_name="party color", max_length=255, blank=True, null=True)
    # party_is_write_in = models.CharField(verbose_name="party affiliation", choices=PARTY_ISWRITE_IN_CHOICES,
    #                                       max_length=16, default=False, blank=False, null=False)
    # for now we are not handling party_color as it is not seen in the CTCL data so far. Refer to this link for details
    # http://vip-specification.readthedocs.io/en/release/built_rst/xml/elements/party.html#multi-xml-party

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_party_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "party" = tells us this is a unique id for a party
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}party{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(Party, self).save(*args, **kwargs)


class PartyManager(models.Model):

    def update_or_create_party(self, party_id_temp='', ctcl_uuid='', party_name='', updated_values={}):
        """
        Either update or create a party entry.
        """
        exception_multiple_object_returned = False
        created = False

        if not party_id_temp:
            success = False
            status = 'MISSING_PARTY_TEMP_ID'
        elif not party_name:
            success = False
            status = 'MISSING_PARTY_NAME'
        else:
            new_party, created = Party.objects.update_or_create(
                party_id_temp=party_id_temp,
                ctcl_uuid=ctcl_uuid,
                defaults=updated_values)
            if new_party or len(new_party):
                success = True
                status = 'PARTY_SAVED'
            else:
                success = False
                created = False
                status = 'PARTY_NOT_UPDATED_OR_CREATED'

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_party_created':        created,
        }
        return results

    def retrieve_all_party_names_and_ids(self):
        """
        Retrieves party name and corresponding party_id_temp from the database
        :return:
        """
        party_items_list = []
        try:
            # retrieve party_id and the corresponding party_name from the table
            party_items_list = Party.objects.using('readonly').values('party_id_temp', 'party_name')
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        return party_items_list

