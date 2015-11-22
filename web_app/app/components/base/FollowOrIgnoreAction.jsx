import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class FollowOrIgnoreAction extends React.Component {
	render() {
		return (
<span>
    <ButtonToolbar>
        <Button bsStyle="info">Follow</Button>
        <Button bsStyle="danger" bsSize="xsmall">Ignore</Button>
    </ButtonToolbar>
</span>
        );
	}
}
