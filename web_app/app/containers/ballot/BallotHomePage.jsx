import axios from 'axios';
import BallotFeedNavigation from "components/base/BallotFeedNavigation";
import BallotFeedItemActionBar from "components/base/BallotFeedItemActionBar";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import InfoIconAction from "components/base/InfoIconAction";
import { Link } from "react-router";
import React from "react";
import StarAction from "components/base/StarAction";
import styles from "./BallotHomePage.css";
import linksCSS from "assets/css/links.css";

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
    <StarAction we_vote_id={'wvcand001'} />
    US House - District 12
    <InfoIconAction we_vote_id={'wvcand001'} />
	<ul className="list-group">
	  <li className="list-group-item">
          <StarAction we_vote_id={'wvcand001'} />
          <div className="row">
            <div className="pull-left col-xs-4 col-md-4">
              <i className={styles.iconXlarge + " icon-icon-person-placeholder-6-1 icon-light"}></i>
            </div>
            <div className="pull-right col-xs-8  col-md-8">
              <h4 className={styles.bufferNone}>
                <Link className={linksCSS.linkLight} to="ballot_candidate" params={{id: 2}}>
                  Fictional Candidate{/* TODO icon-person-placeholder */}
                </Link>
              </h4>
              <p className={styles.typeXLarge}>7 support <span className="small">(more)</span></p>
              <p className={styles.bufferNone}>3 oppose</p>
            </div>
          </div>
          <BallotFeedItemActionBar />
      </li>
    <li className="list-group-item">
        <StarAction we_vote_id={'wvcand001'} />
        <div className="row">
          <div className="pull-left col-xs-4 col-md-4">
            <i className={styles.iconXlarge + " icon-icon-person-placeholder-6-1 icon-light"}></i>
          </div>
          <div className="pull-right col-xs-8  col-md-8">
            <h4 className={styles.bufferNone}>
              <Link className={linksCSS.linkLight} to="ballot_candidate" params={{id: 2}}>
                Another Candidate{/* TODO icon-person-placeholder */}
              </Link>
            </h4>
            <p className={styles.bufferNone}>1 support <span className="small">(more)</span></p>
            <p className={styles.typeXLarge}>8 oppose</p>
          </div>
        </div>
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
              <p className={styles.bufferNone}>1 support <span className="small">(more)</span></p>
              <p className={styles.typeXLarge}>8 oppose</p>
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

<BallotMajorNavigation />
</div>
		);
	}
}
