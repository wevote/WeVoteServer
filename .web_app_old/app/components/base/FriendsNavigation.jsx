"use strict";

import React from "react";
import { Link } from "react-router";

// This navigation is for simple returns to prior page. Does NOT include other options like "More Opinions".
export default class FriendsNavigation extends React.Component {
	render() {
        var alignCenter = {
            margin: 'auto',
            width: '100%'
        };
		return (
<span style={alignCenter}>
    <Link to="requests">Requests</Link>&nbsp;&nbsp;&nbsp;
    Friends&nbsp;&nbsp;&nbsp;
    <Link to="add_friends">Add Friends</Link>
</span>
        );
	}
}
