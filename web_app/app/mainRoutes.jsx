import React from "react";
import { Route, DefaultRoute, NotFoundRoute } from "react-router";

/* eslint-disable no-multi-spaces */
// Only import from `route-handlers/*`
import AddFriendsPage			    	from "route-handlers/AddFriendsPage";
import AddFriendsConfirmedPage			from "route-handlers/AddFriendsConfirmedPage";
import AddFriendsFromAddressPage		from "route-handlers/AddFriendsFromAddressPage";
import AddFriendsMessagePage			from "route-handlers/AddFriendsMessagePage";
import Application  					from "route-handlers/Application";
import AskOrSharePage			    	from "route-handlers/AskOrSharePage";
import BallotCandidatePage				from "route-handlers/BallotCandidatePage";
import BallotCandidateOnePositionPage	from "route-handlers/BallotCandidateOnePositionPage";
import BallotCandidateOpinionsPage		from "route-handlers/BallotCandidateOpinionsPage";
import BallotMeasurePage				from "route-handlers/BallotMeasurePage";
import BallotMeasureOnePositionPage		from "route-handlers/BallotMeasureOnePositionPage";
import BallotMeasureOpinionsPage		from "route-handlers/BallotMeasureOpinionsPage";
import BallotOpinionsPage				from "route-handlers/BallotOpinionsPage";
import BallotHomePage					from "route-handlers/BallotHomePage";
import HomePage     					from "route-handlers/HomePage";
import MorePage							from "route-handlers/MorePage";
import MoreChangeLocationPage			from "route-handlers/MoreChangeLocationPage";
import NotFoundPage 					from "route-handlers/NotFoundPage";
import ReadmePage   					from "route-handlers/ReadmePage";
import VolunteerChooseTask				from "route-handlers/VolunteerChooseTask";
import VolunteerHomePage				from "route-handlers/VolunteerHomePage";
/* eslint-enable */

// polyfill
if(!Object.assign)
	Object.assign = React.__spread; // eslint-disable-line no-underscore-dangle

// export routes
module.exports = (
	<Route name="app" path="/" handler={Application}>
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
		<Route name="home" path="/home" handler={HomePage} />
		<Route name="more" path="/more" handler={MorePage} />
		<Route name="more_change_location" path="/change_location" handler={MoreChangeLocationPage} />
		<Route name="readme" path="/readme" handler={ReadmePage} />
		<Route name="volunteer" path="/volunteer" handler={VolunteerHomePage} />
		<Route name="volunteer_choose_task" path="/volunteer/tasks" handler={VolunteerChooseTask} />
		<DefaultRoute handler={HomePage} />
		<NotFoundRoute handler={NotFoundPage} />
	</Route>
);
