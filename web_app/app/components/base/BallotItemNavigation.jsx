import React from "react";
import { Link } from "react-router";

// This navigation is for returns to prior page, combined with the option to select "More Opinions".
export default class BallotItemNavigation extends React.Component {
	render() {
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top">
                <div className="container-fluid">
                    <div className="left-inner-addon">
                        {/* Create switch between "Back" and "Back to My Ballot" */}
                        <p className="text-left">
                          {(() => {
                            switch (this.props.back_to_ballot) {
                              case 'True':
                                  return <div>
                                      <Link to="ballot">&lt; Back to My Ballot</Link>
                                  </div>;
                              default:
                                  return <div>
                                      <Link to="ballot">&lt; Back</Link>
                                  </div>;
                            }
                          })()}
                            </p>
                        {/* Create switch between ballot_candidate_opinions and ballot_measure_opinions */}
                        <p className="text-right"><Link to="ballot_candidate_opinions"><span className="icon_more_opinions"></span>&nbsp;More Opinions</Link></p>
                    </div>
                </div>
            </nav>
		</div>;
	}
}
