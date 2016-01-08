import axios from 'axios';
import VoterGuideEditSupportOpposeActionBar from "components/base/VoterGuideEditSupportOpposeActionBar";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import { Modal, ModalClose } from 'react-modal-bootstrap';
import React from "react";
import { Alert, Button, ButtonToolbar, Input, Navbar, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";
import Switch from "react-bootstrap-switch";

export default class GuidesVoterEditPage extends React.Component {
	constructor(props) {
		super(props);
        this.state = {
          isEditIntroductionOpen: false
        };
    }

    openEditIntroductionModel = () => {
        this.setState({
            isEditIntroductionOpen: true
        });
    }

    hideEditIntroductionModel = () => {
        this.setState({
            isEditIntroductionOpen: false
        });
    }

	static getProps() {
		return {};
	}

	render() {
        var incoming_message;
        if(this.props.complete == 'true')
        {
        } else {
        }
        incoming_message = <div>
                <ProgressBar striped bsStyle="success" now={100} label="%(percent)s% Complete" />
                <Alert bsStyle="success">
                Your voter guide is ready to publish.
                </Alert>
            </div>;
        var floatRight = {
            float: 'right'
        };
	    return (
<div>
    <HeaderBackNavigation header_text={"Edit Voter Guide"} back_to_text={"< Back to Guides"} link_route={'guides_voter'} />
	<div className="container-fluid well well-90">

        {incoming_message}
        <span style={floatRight}>
            <Link to="guides_voter_edit_settings" params={{guide_id: 27}}>
                <Button bsStyle="primary" bsSize="xsmall">Settings</Button>
            </Link>
        </span>
        <h4>My Voter Guide</h4>
        <div>
            Voter Guide is
            <span>
                <Switch onText="Published" offText="Not Published" /> {/* TODO How do we get react-bootstrap-switch styles to work? */}
            </span>
        </div>
        <p>Voter guide introduction text that the public sees.
        Voter guide introduction text that the public sees.
        Voter guide introduction text that the public sees.
            (<a href="#" onClick={this.openEditIntroductionModel}>edit</a>)
        </p>
        <p>Search for more ballot items to include.</p>
        <Input type="text" name="ballot_item_keyword" className="form-control"
               placeholder="Enter keywords, or a location" />
        <span style={floatRight}>
            <Link to="guides_voter_ballot_results" params={{guide_id: 27}}>
                <Button bsStyle="primary">Search</Button>
            </Link>
        </span>
        <br />
        <div>
            US House - District 12
            <span>
                <Switch onText="Show" offText="Hide" /> {/* TODO How do we get react-bootstrap-switch styles to work? */}
            </span>
            <p>This office is important because... text here text here text here text here
                text here text here text here text here text here
                (edit)
                </p>
        </div>
        <br />
        <div>
            Fictional Candidate
            <span className={floatRight}>
                <Switch onText="Show" offText="Hide" /> {/* TODO How do we get styles to work? */}
            </span>
            <VoterGuideEditSupportOpposeActionBar pronoun={"I"} />
            <p>Fictional candidate should get your support because... text here text here text here text here
                text here text here text here text here text here
                (edit)
                </p>
        </div>
    </div>




    {/* Edit the voter guide introduction */}
    <Modal isOpen={this.state.isEditIntroductionOpen} onRequestHide={this.hideEditIntroductionModel}>
        <div className='modal-header'>
            <ModalClose onClick={this.hideEditIntroductionModel}/>
            <h4 className='modal-title'>Edit Voter Guide Introduction</h4>
        </div>
        <div className='modal-body'>
            <Input type="textarea" defaultValue="Voter guide introduction text that the public sees.
            Voter guide introduction text that the public sees.
            Voter guide introduction text that the public sees."
                   placeholder="Enter text that introduces your voter guide." />
        </div>
        <div className='modal-footer'>
            <button className='btn btn-default' onClick={this.hideEditIntroductionModel}>
              cancel
            </button>
            <button className='btn btn-primary'>
              Save changes
            </button>
        </div>
    </Modal>


</div>
		);
	}
}
