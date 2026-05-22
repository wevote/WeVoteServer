from enum import Enum

class SpeedStatistics(Enum):
    RET_POLITICIAN_FF_ERROR = {
        "name": "Retrieve politician form fields",
        "description": "These is done becase there was an error on the edit_process_view and the voter needs to try again",
    }
    RET_POLITICIAN_SEO = {
        "name": "PoliticianSEOFriendlyPath",
        "description": "Retrieve PoliticianSEOFriendlyPath objects for this politician",
    }
    RET_ORGS = {
        "name": "Find organization(s) connected to this politician by politician_we_vote_id",
        "description": "Retrieve Organization objects for this politician",
    }
    ATT_FOLLOW_ORG = {
        "name": "Attach FollowOrganization information",
        "description": "Attach organization_is_following_politician to the position",
    }
    RET_CANDIDATES = {
        "name": "Find Candidate children of this politician",
        "description": "Retrieve CandidateCampaign objects for this politician",
    }
    RET_CANDIDATES_MATCH = {
        "name": "Find possible Candidate duplicates of this politician",
        "description": "Retrieve CandidateCampaign objects for this politician",
    }
    RET_DUPLICATE_POLITICIANS = {
        "name": "Find possible duplicate politicians",
        "description": "Retrieve Politician objects for this politician",
    }
    RET_REPS_LINKED = {
        "name": "Find Representatives Linked to this Politician",
        "description": "Retrieve Representative objects for this politician",
    }
    RET_REPS_TO_LINK = {
        "name": "Find Representatives to Link to this Politician",
        "description": "Retrieve Representative objects for this politician",
    }
    RET_CAMPAIGNX = {
        "name": "Find Campaigns Linked to this Politician",
        "description": "Retrieve CampaignX objects for this politician",
    }
    RET_POL_LINKED_CAMPAIGNX = {
        "name": "PoliticianLinkedCampaignxWeVoteId",
        "description": "Retrieve politician_linked_campaignx_we_vote_id",
    }
    RET_REC_POLITICIANS = {
        "name": "Find Recommendations related to this Politician",
        "description": "Retrieve RecommendedPoliticianLinkByPolitician objects for this politician",
    }
    POL_CHANGE_LOG = {
        "name": "PoliticianChangeLogFilter",
        "description": "Query PoliticianChangeLog and filter on politician_we_vote_id, order by log_datetime",
    }
    BG_COLOR = {
        "name": "Background Color Generation",
        "description": "Generate background color for politician profile image",
    }
    RET_POLITICIAN_FF = {
        "name": "Retrieve politician form fields",
        "description": "Retrieve form fields from Post request",
    }
    RET_EXISTING_POLITICIAN = {
        "name": "Retrieve existing politician",
        "description": "Retrieve existing politician from db",
    }
    RET_POLITICIAN_DUPS = {
        "name": "Retrieve existing politician duplicates",
        "description": "Retrieve existing politician duplicates from db",
    }
    SET_URL_VARS = {
        "name": "Set url_variables",
        "description": "Set url_variables for redirect",
    }
    CREATE_POLITICIAN = {
        "name": "Create new politician",
        "description": "Create new politician object and name and state code.",
    }
    UP_IMG = {
        "name": "Process incoming uploaded photo if there is one",
        "description": "Process incoming uploaded photo if there is one",
    }
    PROC_FIELDS = {
        "name": "Process politician fields",
        "description": "Processing all other fields in field",
    }
    PROC_TWITTER_URL_POLITICAL_PARTY = {
        "name": "Process politician Twitter, url, political_party fields",
        "description": "Process politician Twitter, url, political_party fields",
    }
    PROC_SEO_PATH = {
        "name": "Process or generate SEO friendly path",
        "description": "Process or generate SEO friendly path",
    }
    PROC_TIKTOK = {
        "name": "Process tiktok_url field",
        "description": "Process tiktok_url field",
    }
    PROC_TWITTER_FAILING = {
        "name": "Process twitter_handle_updates_failing field",
        "description": "Process twitter_handle_updates_failing field",
    }
    PROC_IDS = {
        "name": "Process Ids",
        "description": "Process vote_smart_id, politician_we_vote_id, vote_usa_politician_id, wikipedia_url, youtube_url fields if they exist",
    }
    SAVE_POLITICIAN = {
        "name": "Save politician",
        "description": "Save politician object",
    }
    PROC_BALLOTPEDIA = {
        "name": "Process ballotpedia_politician_url field",
        "description": "Process ballotpedia_politician_url field",
    }
    UP_CAMPAIGNX = {
        "name": "Update CampaignX from politician",
        "description": "Update linked CampaignX from politician if one is found",
    }
    UP_REPRESENTATIVE = {
        "name": "Update Representative from politician",
        "description": "Update linked Representative from politician if one is found",
    }
    RET_REP_MNGR_FAIL = {
        "name": "Query Representative Manager",
        "description": "Queried Representative Manager, but no Representative found for this politician.",
    }
    UP_PRLL_FIELDS = {
        "name": "Update parallel fields",
        "description": "Update parallel fields with years in related objects",
    }
    UNLNK_CANDIDATES = {
        "name": "Unlink Candidates",
        "description": "Unlink Candidates",
    }
    UNLNK_REPS = {
        "name": "Unlink Representatives",
        "description": "Unlink Representatives",
    }
    RET_CANDIDATES_TO_LINK = {
        "name": "Find Candidates to Link",
        "description": "Retrieve Candidates to Link",
    }
    LINK_CANDIDATES = {
        "name": "Link Candidates",
        "description": "Link Candidates",
    }
    LINK_REPS = {
        "name": "Link Representatives",
        "description": "Link Representatives",
    }
    UP_SEO = {
        "name": "Update seo_friendly_path(s)",
        "description": "Update linked CampainXs, Candidates, Representatives with seo_friendly_path",
    }
    UP_SUPS_COUNT = {
        "name": "Update supporters_count",
        "description": "Update supporters_count",
    }
    CHANGE_LOG_VOLUNTEER = {
        "name": "Change log and volunteer scoring",
        "description": "Change log and volunteer scoring",
    }
    UP_MSGS = {
        "name": "Update needed messages",
        "description": "Update needed messages",
    }