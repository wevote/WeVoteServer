'use strict';

// TODO When we upgrade to react@0.14.0 we can use react-intl@2.0.0-beta-1
//import ReactDOM from 'react-dom';
//import {IntlProvider, FormattedNumber, FormattedPlural} from 'react-intl';
// Example code here: https://github.com/yahoo/react-intl
// npm install react-intl@next
import LanguageSwitchNavigation from "../components/base/LanguageSwitchNavigation.jsx";
import React from "react";
import { Button, Input } from "react-bootstrap";
import { Link } from "react-router";

import {voterCount, organizationCount} from '../service/api.js';

export default class Home extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			voter_count: null,
			organization_count: null
		};
	}

	static getProps() {
		return {};
	}

	componentDidMount() {
		this.getOrganizationCount();
		this.getVoterCount();
	}

	getVoterCount() {
		voterCount()
			.then(
                (count) => this.setState({
	               voter_count: count
                })
            );
	}

    getOrganizationCount() {
        organizationCount()
            .then(
                (count) => this.setState({
                    organization_count: count
                })
            );
    }

	render() {
		return (
			<div className="container-fluid well well-90">
			    <h2 className="text-center">We Vote Social Voter Guide</h2>
			    <ul className="list-group">
			    <li className="list-group-item">Research ballot items</li>
			    <li className="list-group-item">Learn from friends</li>
			    <li className="list-group-item">Take to the polls</li>
			    </ul>

			    <ul className="list-group">
			      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;Neutral and private</li>
			      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;{this.state.voter_count} voters</li>
			        {/* TODO When we upgrade to react@0.14.0 we can use react-intl@2.0.0-beta-1
			        <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;
			    <FormattedNumber value={this.state.voterCount} /> {' '}
			    <FormattedPlural value={this.state.voterCount}
			        one="voter"
			        other="voters"
			    /></li>*/}
			      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;{this.state.organization_count} not-for-profit organizations</li>
			      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;and you.</li>
			    </ul>
			    <label htmlFor="address">My Ballot Location</label><br />
			    <span className="small">This is our best guess - feel free to change</span>
			    <Input type="text" name="address" className="form-control" defaultValue="Oakland, CA" />
			    <Link to="intro_opinions">
			        <Button bsStyle="primary">Go</Button>
			    </Link>
			    <br />
			    <br />
			    <LanguageSwitchNavigation />
			</div>
		);
	}
}

// TODO When we upgrade to react@0.14.0 we can use react-intl@2.0.0-beta-1
//ReactDOM.render(
//    <IntlProvider locale="en">
//        <App />
//    </IntlProvider>,
//    document.getElementById('container')
//);
