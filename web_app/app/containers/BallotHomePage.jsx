import axios from 'axios';
import BallotFeedNavigation from "components/base/BallotFeedNavigation";
import BallotFeedItemActionBar from "components/base/BallotFeedItemActionBar";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";
import React from "react";

{/* VISUAL DESIGN HERE: https://invis.io/V33KV2GBR */}

export default class BallotHomePage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
<BallotFeedNavigation />
  <div className="well well-sm split-top-skinny">
    <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;<span className="small">US House - District 12</span>
  </div>
	<ul className="list-group">
	  <li className="list-group-item">
          <Link to="ballot_candidate" params={{id: 2}}>
		    <span className="icon_person"></span>&nbsp;Fictional Candidate
          </Link>
          <span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
          <br />
          7 support (more)<br />
          3 oppose<br />
          <BallotFeedItemActionBar />
      </li>
	  <li className="list-group-item">
          <span className="icon_person"></span>&nbsp;Another Candidate
          <span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
          <br />
          1 support (more)<br />
          8 oppose<br />
          <BallotFeedItemActionBar />
      </li>
	</ul>

	<ul className="list-group">
	  <li className="list-group-item">
          <Link to="ballot_measure" params={{id: 2}}>
              <span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;Measure AA
          </Link>
          <span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
          <br />
          1 support (more)<br />
          8 oppose<br />
          <BallotFeedItemActionBar />
      </li>
	</ul>
<BallotMajorNavigation />
</div>
		);
	}
}
