"use strict";

import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class ElectionsListNavigation extends React.Component {
	render() {
        var floatRight = {
            float: 'right'
        };
        var link_edit;
        if (this.props.link_route_edit) {
            link_edit = <span style={floatRight}>
                <ButtonToolbar>
                    <Link to={this.props.link_route_edit} params={{guide_id: 27}}>
                        <Button bsStyle="info">Edit</Button>
                    </Link>
                </ButtonToolbar>
            </span>;
        }
        var link_route;
        if (this.props.link_route) {
            link_route = this.props.link_route;
        } else {
            link_route = 'guides_voter';
        }
		return (
<span>
	<ul className="list-group">
        <li className="list-group-item">
            {link_edit}
            <Link to={link_route} params={{guide_id: 27}}>
                Primary Election, California<br />
                    <span className="small">
                        March 1, 2016
                    </span>
            </Link>
        </li>
        <li className="list-group-item">
            {link_edit}
            <Link to={link_route} params={{guide_id: 27}}>
            General Election, California<br />
                <span className="small">
                    November 2, 2016
                </span>
            </Link>
        </li>
	</ul>
</span>
        );
	}
}
