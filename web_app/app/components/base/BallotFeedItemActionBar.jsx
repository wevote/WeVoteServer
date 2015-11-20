import React from "react";
import { Link } from "react-router";

// This is the Support, Oppose, Comment and Ask bar under each ballot item
export default class BallotFeedItemActionBar extends React.Component {
	render() {
        var support_item;
        if (this.props.support_on) {
            support_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-up"></span>&nbsp;Support &nbsp;</Link>;
        } else {
            support_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-up"></span>&nbsp;Support &nbsp;</Link>;
        }

        var oppose_item;
        if (this.props.oppose_on) {
            oppose_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-down"></span>&nbsp;Oppose &nbsp;</Link>;
        } else {
            oppose_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-arrow-down"></span>&nbsp;Oppose &nbsp;</Link>;
        }

        var comment_item;
        if (this.props.comment_on) {
            comment_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-comment"></span>&nbsp;Comment &nbsp;</Link>;
        } else {
            comment_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-comment"></span>&nbsp;Comment &nbsp;</Link>;
        }

        var ask_item;
        if (this.props.ask_on) {
            ask_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-share-alt"></span>&nbsp;Ask &nbsp;</Link>;
        } else {
            ask_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-share-alt"></span>&nbsp;Ask &nbsp;</Link>;
        }

		return (
<div className="row">
    <div className="container-fluid">
        <div className="left-inner-addon">
            {/* We switch between "Back" and "Back to My Ballot" */}
            {support_item}
            {oppose_item}
            {comment_item}
            {ask_item}
        </div>
    </div>
</div>
        );
	}
}
