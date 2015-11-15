import React from "react";
import { Route, DefaultRoute, NotFoundRoute } from "react-router";

/* eslint-disable no-multi-spaces */
// Only import from `route-handlers/*`
import Application  		from "route-handlers/Application";
import BallotHomePage		from "route-handlers/BallotHomePage";
import HomePage     		from "route-handlers/HomePage";
import MorePage				from "route-handlers/MorePage";
import NotFoundPage 		from "route-handlers/NotFoundPage";
import ReadmePage   		from "route-handlers/ReadmePage";
import VolunteerChooseTask	from "route-handlers/VolunteerChooseTask";
import VolunteerHomePage	from "route-handlers/VolunteerHomePage";
/* eslint-enable */

// polyfill
if(!Object.assign)
	Object.assign = React.__spread; // eslint-disable-line no-underscore-dangle

// export routes
module.exports = (
	<Route name="app" path="/" handler={Application}>
		<Route name="ballot" path="/ballot" handler={BallotHomePage} />
		<Route name="home" path="/home" handler={HomePage} />
		<Route name="more" path="/more" handler={MorePage} />
		<Route name="readme" path="/readme" handler={ReadmePage} />
		<Route name="volunteer" path="/volunteer" handler={VolunteerHomePage} />
		<Route name="volunteer_choose_task" path="/volunteer/tasks" handler={VolunteerChooseTask} />
		<DefaultRoute handler={HomePage} />
		<NotFoundRoute handler={NotFoundPage} />
	</Route>
);
