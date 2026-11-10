"""Current candidate engagement totals for an election, read from the source database."""

from collections import defaultdict

from django.db.models import Q

from candidate.models import CandidateCampaign, CandidateToOfficeLink
from follow.models import FOLLOWING, FOLLOW_DISLIKE, FollowOrganization
from organization.models import Organization
from politician.models import Politician
from position.models import OPPOSE, SUPPORT, PositionEntered, PositionForFriends
from voter.models import Voter


def calculate_candidate_metrics(election_id):
    links = CandidateToOfficeLink.objects.using('readonly').filter(
        google_civic_election_id=election_id).values_list('candidate_we_vote_id', flat=True)
    candidates = list(CandidateCampaign.objects.using('readonly').filter(
        we_vote_id__in=links).values('id', 'we_vote_id', 'politician_we_vote_id'))
    by_id = {row['id']: row['we_vote_id'] for row in candidates}
    candidate_ids = {row['we_vote_id'] for row in candidates}
    politician_candidates = defaultdict(set)
    for row in candidates:
        if row['politician_we_vote_id']:
            politician_candidates[row['politician_we_vote_id']].add(row['we_vote_id'])
    claimed_politicians = Politician.objects.using('readonly').filter(
        we_vote_id__in=politician_candidates, is_claimed_profile=True).values_list('we_vote_id', flat=True)
    claimed_candidates = set()
    for politician_id in claimed_politicians:
        claimed_candidates.update(politician_candidates[politician_id])

    organizations = list(Organization.objects.using('readonly').filter(
        politician_we_vote_id__in=politician_candidates).values('id', 'we_vote_id', 'politician_we_vote_id'))
    org_candidates = {row['we_vote_id']: politician_candidates[row['politician_we_vote_id']]
                      for row in organizations}
    org_by_id = {row['id']: row['we_vote_id'] for row in organizations}
    follows = list(FollowOrganization.objects.using('readonly').filter(
        Q(organization_we_vote_id__in=org_candidates) | Q(organization_id__in=org_by_id),
        following_status__in=[FOLLOWING, FOLLOW_DISLIKE]).values(
            'voter_id', 'organization_we_vote_id', 'organization_id', 'following_status'))

    positions = []
    for model in (PositionEntered, PositionForFriends):
        positions.extend(model.objects.using('readonly').filter(
            Q(candidate_campaign_we_vote_id__in=candidate_ids) |
            Q(candidate_campaign_id__in=by_id) |
            ((Q(candidate_campaign_we_vote_id='') | Q(candidate_campaign_we_vote_id__isnull=True)) &
             Q(politician_we_vote_id__in=politician_candidates)),
            stance__in=[SUPPORT, OPPOSE],
        ).exclude(is_private_citizen=False).values(
            'voter_id', 'voter_we_vote_id', 'candidate_campaign_we_vote_id',
            'candidate_campaign_id', 'politician_we_vote_id', 'stance'))

    voter_ids = {row['voter_id'] for row in follows + positions if row['voter_id']}
    voter_we_vote_ids = {row['voter_we_vote_id'] for row in positions if row['voter_we_vote_id']}
    voters = list(Voter.objects.using('readonly').filter(
        Q(id__in=voter_ids) | Q(we_vote_id__in=voter_we_vote_ids)))
    voter_by_id = {voter.id: voter for voter in voters}
    voter_by_we_vote_id = {voter.we_vote_id: voter for voter in voters}
    # The existing analytics cache avoids authentication lookups for known signed-in voters.
    follow_voter_ids = {row['voter_id'] for row in follows}
    signed_in_ids = {voter.id for voter in voters if voter.id in follow_voter_ids and
                     (voter.is_signed_in_cached is True or voter.is_signed_in())}

    favorites, dislikes, chosen, opposed = set(), set(), set(), set()
    for row in follows:
        if row['voter_id'] not in signed_in_ids:
            continue
        organization_id = row['organization_we_vote_id'] or org_by_id.get(row['organization_id'])
        target = favorites if row['following_status'] == FOLLOWING else dislikes
        target.update((row['voter_id'], candidate_id)
                      for candidate_id in org_candidates.get(organization_id, ()))
    for row in positions:
        voter = voter_by_id.get(row['voter_id']) or voter_by_we_vote_id.get(row['voter_we_vote_id'])
        if voter is None:
            continue
        candidate_id = row['candidate_campaign_we_vote_id'] or by_id.get(row['candidate_campaign_id'])
        # An explicit candidacy takes precedence over its politician's other candidacies.
        has_explicit_candidate = bool(row['candidate_campaign_we_vote_id'] or row['candidate_campaign_id'])
        targets = ({candidate_id} & candidate_ids) if has_explicit_candidate else politician_candidates.get(
            row['politician_we_vote_id'], set())
        target = chosen if row['stance'] == SUPPORT else opposed
        target.update((voter.id, candidate_id) for candidate_id in targets)

    metrics = {'candidate_count_claimed': len(claimed_candidates)}
    for name, pairs in (
            ('candidate_favorites_count', favorites), ('candidate_dislikes_count', dislikes),
            ('candidates_chosen_count', chosen), ('candidates_opposed_count', opposed)):
        metrics[name] = len(pairs)
        metrics[name + '_claimed'] = sum(candidate_id in claimed_candidates for _, candidate_id in pairs)
    return metrics
