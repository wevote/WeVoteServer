import React from "react";
import { Route, DefaultRoute, NotFoundRoute } from "react-router";

/* eslint-disable no-multi-spaces */
// Only import from `route-handlers/*`
import Application  from "route-handlers/Application";
import ReadmePage   from "route-handlers/ReadmePage";
import HomePage     from "route-handlers/HomePage";
import NotFoundPage from "route-handlers/NotFoundPage";
/* eslint-enable */

// polyfill
if(!Object.assign)
	Object.assign = React.__spread; // eslint-disable-line no-underscore-dangle

// export routes
module.exports = (
	<Route name="app" path="/" handler={Application}>
		<Route name="readme" path="/readme" handler={ReadmePage} />
		<Route name="home" path="/home" handler={HomePage} />
		<DefaultRoute handler={HomePage} />
		<NotFoundRoute handler={NotFoundPage} />
	</Route>
);
