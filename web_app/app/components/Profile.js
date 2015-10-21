var React = require('react');
var Router = require('react-router');
var UserProfile = require('/Users/UserProfile');
var helpers = require('./utilities/helpers');

var Profile = React.createClass({
    mixins: [Router.State],
    init: function () {
      // any ajax calls that are redundant put in here
    },
    getInitialState: function () {
        return (
            name: {},
            bio: {}
        )
    },
    componentDidMount: function () {
      this.init();
    },
    componentWillUnmount: function () {

    },
    componentwillReceiveProps: function () {
        // route change?
        this.init();
    },
    render: function () {
        var username = this.getParams().username;
        return (
            <div className="row">
                <div className="col-md-4">
                    User Profile Component -- {username}
                </div>
                <div className="col-md-4">
                    Repos Component
                </div>
                <div className="col-md-4">
                    Notes Compoent
                </div>
            </div>
        )
    }
});

module.exports = Profile;
