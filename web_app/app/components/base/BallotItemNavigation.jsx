import React from "react";
import { Link } from "react-router";

// TODO DALE I would like to try to use this here https://github.com/svenanders/react-breadcrumbs, but this requires
//  react-router@^1.0.0

// This navigation is for returns to prior page, combined with the option to select "More Opinions".
export default class BallotItemNavigation extends React.Component {
	render() {
        var back_to_link;
        if (this.props.back_to_ballot) {
            back_to_link = <Link to="ballot">&lt; Back to My Ballot</Link>;
        } else {
            {/* TODO Add a way to pass in the return url */}
            back_to_link = <Link to="ballot">&lt; Back</Link>;
        }
        var more_opinions_link;
        if (this.props.is_measure) {
            more_opinions_link = <span><i className="icon-icon-more-opinions-2-2 icon-light icon-medium"></i><Link to="ballot_measure_opinions" className="font-darkest fluff-left-narrow" params={{id: 4}}>More Opinions</Link></span>;
        } else {
            more_opinions_link = <span><i className="icon-icon-more-opinions-2-2 icon-light icon-medium"></i><Link to="ballot_candidate_opinions" className="font-darkest fluff-left-narrow" params={{id: 4}}>More Opinions</Link></span>;
        }
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top bottom-separator">
                <div className="container-fluid">
                    <div className="left-inner-addon">
                        {/* We switch between "Back" and "Back to My Ballot" */}
                        <div className="col-xs-6 col-md-6 text-center">{back_to_link}</div>
                        {/* We switch between ballot_candidate_opinions and ballot_measure_opinions */}
                        <div className="col-xs-6 col-md-6 text-center">{more_opinions_link}</div>
                    </div>
                </div>
            </nav>
		</div>;
	}
}

//// This navigation is for simple returns to prior page. Does NOT include other options like "More Opinions".
//export class BallotReturnNavigation extends React.Component {
//	render() {
//        var back_to_link;
//        if (this.props.back_to_ballot) {
//            back_to_link = <Link to="ballot">&lt; Back to My Ballot</Link>;
//        } else {
//            {/* TODO Add a way to pass in the return url */}
//            back_to_link = <Link to="ballot">&lt; Back</Link>;
//        }
//		return <div className="row">
//            <nav className="navbar navbar-main navbar-fixed-top">
//                <div className="container-fluid">
//                    <div className="left-inner-addon">
//                        {/* Switch between "Back" and "Back to My Ballot" */}
//                        <p className="text-left">{back_to_link}</p>
//                    </div>
//                </div>
//            </nav>
//		</div>;
//	}
//}
