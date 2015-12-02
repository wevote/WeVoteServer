import axios from 'axios';
import BallotReturnNavigation from "../../components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class MoreChangeLocationPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<BallotReturnNavigation />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Change Location</h2>
		<div>
			<span className="small">Please enter the address (or just the city) where you registered to
			vote. The more location information you can provide, the more ballot information will
			be visible.</span>
			<input type="text" name="address" className="form-control" defaultValue="Oakland, CA" />
            <span>
                <ButtonToolbar>
                    <Button bsStyle="primary">Save Location</Button>
                </ButtonToolbar>
            </span>
		</div>
	</div>
</div>
		);
	}
}
