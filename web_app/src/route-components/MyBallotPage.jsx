import React, { Component } from "react";
import { Link } from "react-router";


import OfficeStore from 'stores/OfficeStore';
import OfficeActions from 'actions/OfficeActions';

import Office from 'components/objects/Office';

import CandidateActions from 'actions/CandidateActions';

/*****************************************************************************/
                            //\\REMOVE\\//
/*****************************************************************************/
import StarAction from "components/StarAction";
import InfoIconAction from "components/InfoIconAction";

import BallotFeedNavigation from "components/BallotFeedNavigation";
import BallotFeedItemActionBar from "components/BallotFeedItemActionBar";
/*****************************************************************************/


function getOfficeState() {
    var officeItems = OfficeStore.toArray();
    return {
        officeItems
    };
}
{/* VISUAL DESIGN HERE: https://invis.io/V33KV2GBR */}

export default class MyBallotPage extends Component {
	constructor(props) {
		super(props);
        OfficeActions.load();
        this.state = getOfficeState();
	}

    static getProps() {
        return {};
    }

    componentDidMount() {
        OfficeStore.addChangeListener(this._onChange);
    }

    componentWillUnmount() {
        OfficeStore.removeChangeListener(this._onChange);
    }

	render() {
        let {officeItems} = this.state,
            offices = [];

        officeItems.forEach(office => {
            CandidateActions.loadByOfficeId(office.we_vote_id);
            offices.push(
                <Office
                    key={office.we_vote_id}
                    office_name={office.office_name}
                    we_vote_id={office.we_vote_id}
                />
            )
        }
        );
	    return (
			<div>
			    <BallotFeedNavigation />
                { offices }
                <div>
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
                </div>
			</div>
		);
	}

    /*
        eventListener for ballotChange events
     */
    _onChange() {
        this.setState(getOfficeState());
    }
}
