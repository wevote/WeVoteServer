import React from "react";
import axios from 'axios';
import MainMenu from "components/base/MainMenu";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";

export default class MorePage extends React.Component {
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
		axios
			.get('http://localhost:8000/apis/v1/voterCount')
			.then( function(response) {
				let voterCount = response.data['voter_count'];
				this.setState({
				  	voterCount: voterCount,
				});
			}.bind(this))
			.catch( function(response) {
				console.error('Error');
			}.bind(this));
	}

	render() {
	    return (
			<div>
                <MainMenu />
                <div className="container-fluid well well-90">
                    <h2 className="text-center">MORE PAGE</h2>
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
                <BallotMajorNavigation />
			</div>
		);
	}
}
