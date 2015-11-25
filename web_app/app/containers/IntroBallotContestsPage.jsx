"use strict";

import axios from 'axios';
import BottomContinueNavigation from "components/base/BottomContinueNavigation";
import BallotFeedItemActionBar from "components/base/BallotFeedItemActionBar";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import ListTitleNavigation from "components/base/ListTitleNavigation";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";
import React from "react";

{/* VISUAL DESIGN HERE: https://invis.io/QR3NQWRAH */}

export default class IntroBallotContestsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var floatRight = {
            float: 'right'
        };
	    return (
<div>
    <ListTitleNavigation header_text={"What's On My Ballot?"} back_to_on={false} />
    <div className="container-fluid well well-90">
        <p>We have found your ballot for this location:</p>

        <div>
            <p><Link to="more_change_location" className="font-lightest">Oakland, CA (click to change)</Link></p>
        </div>

        <p>Below you can learn more about specific races or measures. Or you can go straight to your full ballot.</p>

        <span style={floatRight}><Link to="ballot">
            <Button bsStyle="primary">Show me My Ballot ></Button>
        </Link></span>
        <br />

        <a name="candidates"></a>
        <h4>Candidates</h4>
        <a href="#measures">Jump to Measures</a>
        <ul className="list-group">
            <li className="list-group-item">
                <Link to="ballot">US House - District 12</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will choose one candidate from among three that are running for this office.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to Candidates ></Button>
                </Link></span>
                <br />
            </li>

            <li className="list-group-item">
                <Link to="ballot">Governor</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will rank your top two choices from among three that are running for this office.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to Candidates ></Button>
                </Link></span>
                <br />
            </li>

            <li className="list-group-item">
                <Link to="ballot">Mayor</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will rank your top three choices from among seven that are running for this office.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to Candidates ></Button>
                </Link></span>
                <br />
            </li>
        </ul>

        <a name="measures"></a>
        <h4>Measures</h4>
        <a href="#candidates">Jump to Candidates</a>
        <ul className="list-group">
            <li className="list-group-item">
                <Link to="ballot">Measure AA</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will vote Yes or No on this Measure.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to this Measure ></Button>
                </Link></span>
                <br />
            </li>

            <li className="list-group-item">
                <Link to="ballot">Measure BB</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will vote Yes or No on this Measure.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to this Measure ></Button>
                </Link></span>
                <br />
            </li>

            <li className="list-group-item">
                <Link to="ballot">Measure CC</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>{/* Right align */}
                <br />
                You will vote Yes or No on this Measure.<br />
                <span style={floatRight}><Link to="ballot">
                    <Button bsStyle="primary" bsSize="xsmall">Go to this Measure ></Button>
                </Link></span>
                <br />
            </li>
        </ul>
    </div>
    <BottomContinueNavigation  link_route_continue={'ballot'} continue_text={'Show me My Ballot'} />
</div>
		);
	}
}
