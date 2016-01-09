import AskOrShareAction from "components/base/AskOrShareAction";
import React from "react";
import { DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";
import ballotHome from "containers/ballot/BallotHomePage.css";
import linksCSS from "assets/css/links.css";

// This is the Support, Oppose, Comment and Ask bar under each ballot item
export default class BallotFeedItemActionBar extends React.Component {
	render() {
        var support_item;
        if (this.props.support_on) {
            support_item = <Link className={linksCSS.linkLight + " " + linksCSS.linkSmall} to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-up"></span>&nbsp;Support &nbsp;</Link>;
        } else {
            support_item = <Link className={linksCSS.linkLight + " " + linksCSS.linkSmall} to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-up"></span>&nbsp;Support &nbsp;</Link>;
        }

        var oppose_item;
        if (this.props.oppose_on) {
            oppose_item = <Link to="ballot" className={linksCSS.linkLight + " " + linksCSS.linkSmall}><span className="glyphicon glyphicon-small glyphicon-arrow-down"></span>&nbsp;Oppose &nbsp;</Link>;
        } else {
            oppose_item = <Link to="ballot" className={linksCSS.linkLight + " " + linksCSS.linkSmall}><span className="glyphicon glyphicon-small glyphicon-arrow-down"></span>&nbsp;Oppose &nbsp;</Link>;
        }

		return (
<div className={ballotHome.borderTop + " " + ballotHome.paddingTopSmall  + " row"}>
    <div className="container-fluid">
        <div className="left-inner-addon">
            {support_item}
            {oppose_item}
            <Link className={linksCSS.linkLight + " " + linksCSS.linkSmall} to="ballot_candidate" params={{id: 2}}><span className="glyphicon glyphicon-small glyphicon-comment"></span>&nbsp;Comment &nbsp;</Link>
            <AskOrShareAction />
        </div>
    </div>
</div>
        );
	}
}
