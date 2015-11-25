"use strict";

import axios from 'axios';
// TODO When we upgrade to react@0.14.0 we can use react-intl@2.0.0-beta-1
//import ReactDOM from 'react-dom';
//import {IntlProvider, FormattedNumber, FormattedPlural} from 'react-intl';
// Example code here: https://github.com/yahoo/react-intl
// npm install react-intl@next
<<<<<<< HEAD
=======
import {get} from '../../lib/service/calls.js'
import LanguageSwitchNavigation from "components/base/LanguageSwitchNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";
>>>>>>> f3431c9b377cb86f21f1293f92f58a7324461ad9

import {voterCount, organizationCount} from '../service/api';

export default class HomePage extends React.Component {
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
<<<<<<< HEAD
        this.getOrganizationCount();
		this.getVoterCount();
=======
		this.getVoterCount()

		// if user does not have a device id set already then set one
		if (docCookies.getItem('deviceId') === null) {
			new Promise( (resolve, reject) => {
				this.generateDeviceId()
					.then( function(response) {
						resolve(response.data['voter_device_id']);
					});
			})
			.then( (deviceId) => {
				docCookies.setItem('deviceId', deviceId);
				this.createVoter(deviceId);
			})
		} else {
			console.log('cookie is already set')
		}
>>>>>>> f3431c9b377cb86f21f1293f92f58a7324461ad9
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
        var alignCenter = {
            margin: 'auto',
            width: '100%'
        };
	    return (
<div className="container-fluid well well-90">
    <h2 className="text-center">We Vote Social Voter Guide</h2>
    <ul className="list-group">
    <li className="list-group-item">Research ballot items</li>
    <li className="list-group-item">Learn from friends</li>
    <li className="list-group-item">Take to the polls</li>
    </ul>

<<<<<<< HEAD
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
				<div>
					<label htmlFor="last-name">My Ballot Location</label><br />
					<span className="small">This is our best guess - feel free to change</span>
					<input type="text" name="address" className="form-control" />
				</div>
			</div>
=======
    <ul className="list-group">
      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;Neutral and private</li>
      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;{this.state.voterCount} voters</li>
        {/* TODO When we upgrade to react@0.14.0 we can use react-intl@2.0.0-beta-1
        <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;
    <FormattedNumber value={this.state.voterCount} /> {' '}
    <FormattedPlural value={this.state.voterCount}
        one="voter"
        other="voters"
    /></li>*/}
      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;417 not-for-profit organizations</li>
      <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;and you.</li>
    </ul>
    <label htmlFor="last-name">My Ballot Location</label><br />
    <span className="small">This is our best guess - feel free to change</span>
    <Input type="text" name="address" className="form-control" defaultValue="Oakland, CA" />
    <Link to="intro_opinions">
        <Button bsStyle="primary">Go</Button>
    </Link>
    <br />
    <br />
    <LanguageSwitchNavigation />
</div>
>>>>>>> f3431c9b377cb86f21f1293f92f58a7324461ad9
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
