"use strict";

import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class FollowOrIgnoreAction extends React.Component {
	render() {
        var floatRight = {
            float: 'right'
        };
		return (
<span style={floatRight}>
    <ButtonToolbar>
        <Button bsStyle="info">Follow</Button>
        <Button bsStyle="danger" bsSize="xsmall">Ignore</Button>
    </ButtonToolbar>
</span>
        );
	}
}
