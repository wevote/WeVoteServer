import React from 'react';
import Router from 'react-router';
import UserProfile from '/Users/UserProfile';
import helpers from './utilities/helpers';

const Profile = React.createClass({
  mixins: [Router.State],
  getInitialState() {
    return (
      name: {},
      //bio: {}
    )
  },
  componentDidMount() {
    this.init();
  },
  componentWillUnmount() {

  },
  init() {

  },
  componentwillReceiveProps() {
      // route change?
      this.init();
  },
  render() {
      const username = this.getParams().username;
      return (
          <div className="row">
              <div className="col-md-8">
                  User Profile Component -- {username}
              </div>
          </div>
      )
  }
});

export default Profile;
