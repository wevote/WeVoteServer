import React from "react";
import { DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";
import linksCSS from "assets/css/links.css";
export default class AskOrShareAction extends React.Component {
	render() {
        var link_text;
        if (this.props.link_text) {
            link_text = this.props.link_text;
        } else {
            link_text = "Ask or Share";
        }
		return (
<span>
    <span className="glyphicon glyphicon-small glyphicon-share-alt"></span>
    <DropdownButton bsStyle="link" className={linksCSS.linkLight + " " + linksCSS.linkSmall} title={link_text} id="17">
        <MenuItem eventKey="1"><Link to="ask_or_share" params={{id: 2}}>Email</Link></MenuItem>
        <MenuItem eventKey="2">Facebook</MenuItem>
        <MenuItem eventKey="3">Twitter</MenuItem>
        <MenuItem eventKey="4">Copy Link</MenuItem>
    </DropdownButton>
</span>
        );
	}
}
