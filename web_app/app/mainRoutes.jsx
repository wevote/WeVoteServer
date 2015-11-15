import React from "react";
import { Route, DefaultRoute, NotFoundRoute } from "react-router";

/* eslint-disable no-multi-spaces */
// Only import from `route-handlers/*`
import Application  					from "route-handlers/Application";
import BallotAddFriendsPage			    from "route-handlers/BallotAddFriendsPage";
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
		<Route name="ballot" path="/ballot" handler={BallotHomePage} />
		<Route name="ballot_add_friends" path="/ballot/addfriends" handler={BallotAddFriendsPage} />
		<Route name="ballot_candidate" path="/ballot/candidate" handler={BallotCandidatePage} />
		<Route name="ballot_candidate_one_position" path="/ballot/candidate/position" handler={BallotCandidateOnePositionPage} />
		<Route name="ballot_candidate_opinions" path="/ballot/candidate/opinions" handler={BallotCandidateOpinionsPage} />
		<Route name="ballot_measure" path="/ballot/measure" handler={BallotMeasurePage} />
		<Route name="ballot_measure_one_position" path="/ballot/measure/position" handler={BallotMeasureOnePositionPage} />
		<Route name="ballot_measure_opinions" path="/ballot/measure/opinions" handler={BallotMeasureOpinionsPage} />
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
