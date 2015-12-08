import React, { Component } from "react";

import { Link } from "react-router";

import BallotFeedNavigation from "components/base/BallotFeedNavigation";
import BallotFeedItemActionBar from "components/base/BallotFeedItemActionBar";
import InfoIconAction from "components/base/InfoIconAction";
import StarAction from "components/base/StarAction";

import BallotStore from 'stores/BallotStore';

function getBallotState() {
    var ballotItems = BallotStore.toArray();
    return {
        ballotItems
    };
}
{/* VISUAL DESIGN HERE: https://invis.io/V33KV2GBR */}

export default class MyBallotPage extends Component {
	constructor(props) {
		super(props);
	}

    static getProps() {
        return getBallotState();
    }

    componentDidMount() {
        BallotStore.addChangeListener(this._onChange);
    }

    componentWillUnmount() {
        BallotStore.removeChangeListener(this._onChange);
    }

	render() {
	    return (
			<div>
			    <BallotFeedNavigation />
			    <div className="well well-sm split-top-skinny">
			    <StarAction we_vote_id={'wvcand001'} />
			    US House - District 12
			    <InfoIconAction we_vote_id={'wvcand001'} />
				<ul className="list-group">
				  <li className="list-group-item">
			          <StarAction we_vote_id={'wvcand001'} />
			          <Link to="candidate" params={{id: 2}}>
					    <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Fictional Candidate{/* TODO icon-person-placeholder */}
			          </Link>
			          <InfoIconAction we_vote_id={'wvcand001'} />
			          <br />
			          7 support (more)<br />
			          3 oppose<br />
			          <BallotFeedItemActionBar />
			      </li>
				  <li className="list-group-item">
			          <StarAction we_vote_id={'wvcand001'} />
			          <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Another Candidate{/* TODO icon-person-placeholder */}
			          <InfoIconAction we_vote_id={'wvcand001'} />
			          <br />
			          1 support (more)<br />
			          8 oppose<br />
			          <BallotFeedItemActionBar />
			      </li>
				</ul>
			  </div>

			  <div className="well well-sm split-top-skinny">
			        <StarAction we_vote_id={'wvcand001'} />
			        <Link to="ballot_measure" params={{id: 2}}>
			          Measure AA
			        </Link>
			        <InfoIconAction we_vote_id={'wvcand001'} />
			        <ul className="list-group">
			            <li className="list-group-item">
			              1 support (more)<br />
			              8 oppose<br />
			              <BallotFeedItemActionBar />
			            </li>
			        </ul>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>

			    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam rutrum sem eu leo rutrum condimentum.
			        Maecenas nibh odio, auctor eget arcu et, auctor vehicula odio. Sed mollis id odio et volutpat.</p>
			  </div>
			</div>
		);
	}

    /*
        eventListener for ballotChange events
     */
    _onChange() {
        this.setState(getBallotState());
    }
}
