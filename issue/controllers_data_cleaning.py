# issue/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import wevote_functions.admin
from organization.models import Organization
from issue.models import OrganizationLinkToIssue

logger = wevote_functions.admin.get_logger(__name__)


def cleanup_organization_links(batch_size= 1000):
    """
    Delete OrganizationLinkToIssue records that reference invalid organizations.
    
    Identifies and deletes links where the organization_we_vote_id does not exist
    in the Organization table.
    
    Returns:
        dict: Status summary with success flag and deletion count
    """
    deleted_count = 0
    invalid_link_ids_to_delete = []
    status = ''
    success = True
    total_checked = 0
    total_remaining = 0
    updates_made = 0
    
    try:
        # Get all valid organization we_vote_ids from Organization table
        valid_org_ids = set(Organization.objects.using('readonly').values_list('we_vote_id', flat=True))
        
        # Query OrganizationLinkToIssue records to verify
        link_to_issue_query = OrganizationLinkToIssue.objects.using('readonly').values_list('id', 'organization_we_vote_id')
        total_to_check = link_to_issue_query.count()
        
        # Find invalid links for deletion
        for link_id, org_we_vote_id in link_to_issue_query.iterator():
            total_checked += 1
            # Check if organization exists in valid set
            if org_we_vote_id not in valid_org_ids:
                invalid_link_ids_to_delete.append(link_id)
                updates_made += 1
        
        # Delete invalid links in batches
        if invalid_link_ids_to_delete:
            try:
                
                for i in range(0, len(invalid_link_ids_to_delete), batch_size):
                    batch_ids = invalid_link_ids_to_delete[i:i + batch_size]
                    batch_deleted_count, _ = OrganizationLinkToIssue.objects.filter(
                        id__in=batch_ids
                    ).delete()
                    deleted_count += batch_deleted_count
                    
                status += "CLEANUP_ORGANIZATION_LINKS_DELETED: " \
                         f"{deleted_count:,} invalid links deleted. " \
                         f"{total_remaining:,} remaining. "
                success = True
            except Exception as e:
                status += f"ERROR_DELETING_ORGANIZATION_LINKS: {str(e)} "
                success = False
                logger.exception(f"Error deleting organization links: {str(e)}")
        else:
            status += "NO_INVALID_LINKS_TO_DELETE: " \
                     f"Checked {total_checked:,} links. " \
                     f"{total_remaining:,} remaining. "
            success = True
    
    except Exception as e:
        status += f"ERROR_CLEANUP_ORGANIZATION_LINKS: {str(e)} "
        success = False
        logger.exception(f"Error in cleanup_organization_links: {str(e)}")
    
    results = {
        'status': status,
        'success': success,
        'deleted_count': deleted_count,
        'total_remaining': total_remaining,
    }
    return results

