import React from "react";

import BallotReturnNavigation from "components/base/BallotReturnNavigation";

{/* VISUAL DESIGN HERE:  */}

export default class TermsAndPolicies extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
				<BallotReturnNavigation back_to_ballot={false} link_route={'more'} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Terms and Policies</h2>
			        Coming soon.
			    </div>
			</div>
		);
	}
}
