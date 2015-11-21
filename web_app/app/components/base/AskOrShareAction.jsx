import React from "react";
import { DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";

export default class AskOrShareAction extends React.Component {
	render() {
		return (
<span>
    <span className="glyphicon glyphicon-small glyphicon-share-alt"></span>
    <DropdownButton bsStyle="link" title="Ask or Share" id="17">
        <MenuItem eventKey="1"><Link to="ask_or_share" params={{id: 2}}>Email</Link></MenuItem>
        <MenuItem eventKey="2">Facebook</MenuItem>
        <MenuItem eventKey="3">Twitter</MenuItem>
        <MenuItem eventKey="4">Copy Link</MenuItem>
    </DropdownButton>
</span>
        );
	}
}
