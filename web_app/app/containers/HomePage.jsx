import React from "react";
import axios from 'axios';

import {get} from '../../lib/service/calls.js'

get('voterCount', function (res) {
	console.log(res);
});

import docCookies from 'cookies';

export default class HomePage extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			voterCount: null,
			organizations: null
		};
	}

	static getProps() {
		return {};
	}

	componentDidMount() {
		this.getVoterCount()

		// if user does not have a device id set already then set one
		if (docCookies.getItem('deviceId') === null) {
			new Promise( function(resolve, reject) {
				this.generateDeviceId()
					.then( function(response) {
						resolve(response.data['voter_device_id']);
					});
			}.bind(this))
			.then( function(deviceId) {
				docCookies.setItem('deviceId', deviceId);
				this.createVoter(deviceId);
			}.bind(this))
		} else {
			console.log('cookie is already set')
		}


	}

	getVoterCount() {
		axios.get('http://localhost:8000/apis/v1/voterCount')
			.then(function (response) {
				let voterCount = response.data['voter_count'];
				this.setState({
					voterCount: voterCount,
				});
			}.bind(this));
	}

	generateDeviceId() {
		return axios.get('http://localhost:8000/apis/v1/deviceIdGenerate');
	}

	createVoter(deviceId) {
		return axios.get('http://localhost:8000/apis/v1/voterCreate', {
				voter_device_id: deviceId
			})
			.then( function (response) {
				console.log(response)
			});
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
				  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;{this.state.voterCount} voters</li>
				  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;417 not-for-profit organizations</li>
				  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;and you.</li>
				</ul>
				<div>
					<label htmlFor="last-name">My Ballot Location</label><br />
					<span className="small">This is our best guess - feel free to change</span>
					<input type="text" name="last-name" className="form-control" />
				</div>
			</div>
		);
	}
}
