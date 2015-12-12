import React from "react";
import { Route, DefaultRoute, NotFoundRoute } from "react-router";

/* eslint-disable no-multi-spaces */
// Only import from `route-handlers/*`
import AboutPage								from "route-handlers/AboutPage";
import AccountSettingsPage						from "route-handlers/AccountSettingsPage";
import ActivityPage								from "route-handlers/ActivityPage";
import AddFriendsPage			    			from "route-handlers/AddFriendsPage";
import AddFriendsConfirmedPage					from "route-handlers/AddFriendsConfirmedPage";
import AddFriendsFromAddressPage				from "route-handlers/AddFriendsFromAddressPage";
import AddFriendsMessagePage					from "route-handlers/AddFriendsMessagePage";
import Application  							from "route-handlers/Application";
import AskOrSharePage			    			from "route-handlers/AskOrSharePage";
import BallotCandidatePage						from "route-handlers/BallotCandidatePage";
import BallotCandidateOnePositionPage			from "route-handlers/BallotCandidateOnePositionPage";
import BallotCandidateOpinionsPage				from "route-handlers/BallotCandidateOpinionsPage";
import BallotMeasurePage						from "route-handlers/BallotMeasurePage";
import BallotMeasureOnePositionPage				from "route-handlers/BallotMeasureOnePositionPage";
import BallotMeasureOpinionsPage				from "route-handlers/BallotMeasureOpinionsPage";
import BallotOpinionsPage						from "route-handlers/BallotOpinionsPage";
import BallotHomePage							from "route-handlers/BallotHomePage";
import ConnectPage								from "route-handlers/ConnectPage";
import DonatePage								from "route-handlers/DonatePage";
import EmailBallotPage							from "route-handlers/EmailBallotPage";
import FramedContentPage						from "route-handlers/FramedContentPage";
import GuidesAddOrganizationPage				from "route-handlers/GuidesAddOrganizationPage";
import GuidesAddOrganizationSearchPage			from "route-handlers/GuidesAddOrganizationSearchPage";
import GuidesAddOrganizationResultsPage			from "route-handlers/GuidesAddOrganizationResultsPage";
import GuidesConfirmOwnershipPage				from "route-handlers/GuidesConfirmOwnershipPage";
import GuidesConfirmOwnershipEmailSentPage		from "route-handlers/GuidesConfirmOwnershipEmailSentPage";
import GuidesOrganizationAddExistingLinkPage	from "route-handlers/GuidesOrganizationAddExistingLinkPage";
import GuidesOrganizationChooseElectionPage		from "route-handlers/GuidesOrganizationChooseElectionPage";
import GuidesOrganizationDisplayPage			from "route-handlers/GuidesOrganizationDisplayPage";
import GuidesOrganizationEditPage				from "route-handlers/GuidesOrganizationEditPage";
import GuidesOrganizationEmailVerifyPage		from "route-handlers/GuidesOrganizationEmailVerifyPage";
import GuidesOrganizationBallotAddItemsPage		from "route-handlers/GuidesOrganizationBallotAddItemsPage";
import GuidesOrganizationBallotResultsPage		from "route-handlers/GuidesOrganizationBallotResultsPage";
import GuidesOrganizationBallotSearchPage		from "route-handlers/GuidesOrganizationBallotSearchPage";
import GuidesOrganizationPersonalEmailPage		from "route-handlers/GuidesOrganizationPersonalEmailPage";
import GuidesOwnershipConfirmedPage				from "route-handlers/GuidesOwnershipConfirmedPage";
import GuidesVoterHomePage						from "route-handlers/GuidesVoterHomePage";
import GuidesVoterAddExistingLinkPage			from "route-handlers/GuidesVoterAddExistingLinkPage";
import GuidesVoterAddTwitterPage				from "route-handlers/GuidesVoterAddTwitterPage";
import GuidesVoterPersonalEmailPage			    from "route-handlers/GuidesVoterPersonalEmailPage";
import GuidesVoterEmailVerifyPage			    from "route-handlers/GuidesVoterEmailVerifyPage";
import GuidesVoterChooseElectionPage			from "route-handlers/GuidesVoterChooseElectionPage";
import GuidesVoterBallotResultsPage			    from "route-handlers/GuidesVoterBallotResultsPage";
import GuidesVoterEditPage			            from "route-handlers/GuidesVoterEditPage";
import GuidesVoterEditSettingsPage			    from "route-handlers/GuidesVoterEditSettingsPage";
import GuidesVoterDisplayPage			        from "route-handlers/GuidesVoterDisplayPage";
import HomePage     							from "route-handlers/HomePage";
import IntroBallotContestsPage					from "route-handlers/IntroBallotContestsPage";
import IntroOpinionsPage						from "route-handlers/IntroOpinionsPage";
import MorePage									from "route-handlers/MorePage";
import MoreChangeLocationPage					from "route-handlers/MoreChangeLocationPage";
import MyFriendsPage							from "route-handlers/MyFriendsPage";
import NotFoundPage 							from "route-handlers/NotFoundPage";
import OpinionsFollowedPage 					from "route-handlers/OpinionsFollowedPage";
import OrgEndorsementsPage 						from "route-handlers/OrgEndorsementsPage";
import ReadmePage   							from "route-handlers/ReadmePage";
import RequestsPage								from "route-handlers/RequestsPage";
import TermsAndPoliciesPage 					from "route-handlers/TermsAndPoliciesPage";
import VolunteerChooseTaskPage						from "route-handlers/VolunteerChooseTaskPage";
import VolunteerFindGuideSearchPage				from "route-handlers/VolunteerFindGuideSearchPage";
import VolunteerHomePage						from "route-handlers/VolunteerHomePage";
/* eslint-enable */

// polyfill
if(!Object.assign)
	Object.assign = React.__spread; // eslint-disable-line no-underscore-dangle

// export routes
module.exports = (
	<Route name="app" path="/" handler={Application}>
		<Route name="about" path="/more/about" handler={AboutPage} />
		<Route name="account_settings" path="/more/account/settings" handler={AccountSettingsPage} />
		<Route name="activity" path="/activity" handler={ActivityPage} />
		<Route name="add_friends" path="/addfriends" handler={AddFriendsPage} />
		<Route name="add_friends_confirmed" path="/addfriends/confirmed" handler={AddFriendsConfirmedPage} />
		<Route name="add_friends_from_address" path="/addfriends/from" handler={AddFriendsFromAddressPage} />
		<Route name="add_friends_message" path="/addfriends/message" handler={AddFriendsMessagePage} />
		<Route name="ask_or_share" path="/ask" handler={AskOrSharePage} />
		<Route name="ballot" path="/ballot" handler={BallotHomePage} />
		<Route name="ballot_candidate" path="/ballot/candidate/:id" handler={BallotCandidatePage} />
		<Route name="ballot_candidate_one_org_position" path="/ballot/candidate/:id/org/:org_id" handler={BallotCandidateOnePositionPage} />
		<Route name="ballot_candidate_opinions" path="/ballot/candidate/:id/opinions" handler={BallotCandidateOpinionsPage} />
		<Route name="ballot_measure" path="/ballot/measure/:id" handler={BallotMeasurePage} />
		<Route name="ballot_measure_one_position" path="/ballot/measure/:id/org/:org_id" handler={BallotMeasureOnePositionPage} />
		<Route name="ballot_measure_opinions" path="/ballot/measure/:id/opinions/" handler={BallotMeasureOpinionsPage} />
		<Route name="ballot_opinions" path="/ballot/opinions" handler={BallotOpinionsPage} />
		<Route name="connect" path="/connect" handler={ConnectPage} />
		<Route name="donate" path="/more/donate" handler={DonatePage} />
		<Route name="email_ballot" path="/more/emailballot" handler={EmailBallotPage} />
		<Route name="framed_content" path="/framed" handler={FramedContentPage} />
		<Route name="guides_organization_confirm_ownership" path="/guides/org/add/confirm" handler={GuidesConfirmOwnershipPage} />
		<Route name="guides_organization_confirm_ownership_email_sent" path="/guides/org/add/confirmemailsent" handler={GuidesConfirmOwnershipEmailSentPage} />
		<Route name="guides_organization_add_search" path="/guides/org/add/search" handler={GuidesAddOrganizationSearchPage} />
		<Route name="guides_organization_add_results" path="/guides/org/add/results" handler={GuidesAddOrganizationResultsPage} />
		<Route name="guides_organization_add" path="/guides/org/add/details" handler={GuidesAddOrganizationPage} />
		<Route name="guides_organization_add_existing_link" path="/guides/org/add/link" handler={GuidesOrganizationAddExistingLinkPage} />
		<Route name="guides_organization_ballot_add_items" path="/guides/org/:guide_id/additems" handler={GuidesOrganizationBallotAddItemsPage} />
		<Route name="guides_organization_ballot_search" path="/guides/org/add/ballotsearch" handler={GuidesOrganizationBallotSearchPage} />
		<Route name="guides_organization_ballot_results" path="/guides/org/add/ballotresults" handler={GuidesOrganizationBallotResultsPage} />
		<Route name="guides_organization_choose_election" path="/guides/org/add/election" handler={GuidesOrganizationChooseElectionPage} />
		<Route name="guides_organization_display" path="/guides/org/:guide_id" handler={GuidesOrganizationDisplayPage} />
		<Route name="guides_organization_edit" path="/guides/org/:guide_id/edit" handler={GuidesOrganizationEditPage} />
		<Route name="guides_organization_email_verify" path="/guides/org/add/emailverify" handler={GuidesOrganizationEmailVerifyPage} />
		<Route name="guides_organization_email" path="/guides/org/add/email" handler={GuidesOrganizationPersonalEmailPage} />
		<Route name="guides_organization_ownership_confirmed" path="/guides/org/add/ownershipconfirmed" handler={GuidesOwnershipConfirmedPage} />
		<Route name="guides_voter" path="/guides/voter/" handler={GuidesVoterHomePage} />
		<Route name="guides_voter_add_existing_link" path="/guides/voter/add/link" handler={GuidesVoterAddExistingLinkPage} />
		<Route name="guides_voter_add_twitter" path="/guides/voter/add/twitter" handler={GuidesVoterAddTwitterPage} />
		<Route name="guides_voter_ballot_results" path="/guides/voter/add/ballotresults" handler={GuidesVoterBallotResultsPage} />
		<Route name="guides_voter_choose_election" path="/guides/voter/add/election" handler={GuidesVoterChooseElectionPage} />
		<Route name="guides_voter_display" path="/guides/voter/:guide_id" handler={GuidesVoterDisplayPage} />
		<Route name="guides_voter_edit" path="/guides/voter/:guide_id/edit" handler={GuidesVoterEditPage} />
		<Route name="guides_voter_edit_settings" path="/guides/voter/:guide_id/editsettings" handler={GuidesVoterEditSettingsPage} />
		<Route name="guides_voter_email_verify" path="/guides/voter/add/emailverify" handler={GuidesVoterEmailVerifyPage} />
		<Route name="guides_voter_email" path="/guides/voter/add/email" handler={GuidesVoterPersonalEmailPage} />
		<Route name="home" path="/home" handler={HomePage} />
		<Route name="intro_contests" path="/intro/contests" handler={IntroBallotContestsPage} />
		<Route name="intro_opinions" path="/intro/opinions" handler={IntroOpinionsPage} />
		<Route name="more" path="/more" handler={MorePage} />
		<Route name="more_change_location" path="/change_location" handler={MoreChangeLocationPage} />
		<Route name="my_friends" path="/friends" handler={MyFriendsPage} />
		<Route name="opinions_followed" path="/opinions" handler={OpinionsFollowedPage} />
		<Route name="org_endorsements" path="/org/:org_id" handler={OrgEndorsementsPage} />
		<Route name="readme" path="/readme" handler={ReadmePage} />
		<Route name="requests" path="/requests" handler={RequestsPage} />
		<Route name="privacy" path="/privacy" handler={TermsAndPoliciesPage} />
		<Route name="volunteer" path="/volunteer" handler={VolunteerHomePage} />
		<Route name="volunteer_choose_task" path="/volunteer/tasks" handler={VolunteerChooseTaskPage} />
		<Route name="volunteer_find_guide" path="/volunteer/find" handler={VolunteerFindGuideSearchPage} />
		<DefaultRoute handler={HomePage} />
		<NotFoundRoute handler={NotFoundPage} />
	</Route>
);
