import React, { Component } from "react";
import { Link } from "react-router";

import AddressBox from 'components/AddressBox/AddressBox';
import Office from 'components/Office';

/*****************************************************************************/
                            //\\REMOVE\\//
/*****************************************************************************/
import StarAction from "components/StarAction";
import InfoIconAction from "components/InfoIconAction";

import BallotFeedNavigation from "components/BallotFeedNavigation";
import BallotFeedItemActionBar from "components/BallotFeedItemActionBar";
/*****************************************************************************/

{/* VISUAL DESIGN HERE: https://invis.io/V33KV2GBR */}
function loadOfficeItems () {

}

export default class MyBallotPage extends Component {
	constructor(props) {
		super(props);

	}

    static getProps() {
        return {};
    }

    componentDidMount() {

    }

    componentWillUnmount() {
    }

    /**
     * save address changes
     * @return {undefined}
     */
    changeSaved(err) {
        if (err) console.error('Issue saving address to server..', err);
        console.log('Ballot page saving...');

    }

	render() {

	    return (
			<div>
            <div className="row">
                <nav className="navbar navbar-main navbar-fixed-top bottom-separator">
                    <div className="container-fluid">
                        <div className="left-inner-addon">
                          <h4 className="pull-left no-space bold">My Ballot</h4>
                          <ul className="nav nav-pills pull-right">
                                <AddressBox changeSaved={this.changeSaved.bind(this)}/>
                          </ul>
                        </div>
                    </div>
                </nav>
                <div className="container-fluid bg-light box-skinny bottom-separator">
                  <div className="row">
                    <div className="col-xs-6 col-md-6 text-center"><i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i><Link to="add_friends" className="font-darkest fluff-left-narrow">Add Friends</Link></div>
                    <div className="col-xs-6 col-md-6 text-center"><i className="icon-icon-more-opinions-2-2 icon-light icon-medium"></i><Link to="ballot_opinions" className="font-darkest fluff-left-narrow">More Opinions</Link></div>
                  </div>
                </div>
            </div>
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
}
