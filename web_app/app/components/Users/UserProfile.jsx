var React = require('react');
var helpers = require('utilities/helpers');

var UserProfile = React.createClass({
  mixins: [Router.state],
  getInitialState: function () {
    return {
      avatar: {url: ''},
      firstName: {firstName: 'Rob'},
      lastName: {lastName: 'Simpson'}
    }
  },
  propTypes: {
    avatar: React.PropTypes.string,
    firstName: React.PropTypes.string.isRequired,
    lastName: React.PropTypes.string.isRequired
  },
  componentDidMount: function () {
    // this is where AJAX is handled
    // called right after the ui renders the view

    helpers.getUserInfo(this.params().firstName)
      .then(function (dataObj) {
        this.setState({
          avatar: dataObj.avatar,
          firstName;
        dataObj.firstName,
          lastName
        :
        dataObj.lastName
      });
  }.bind(this));
},
componentWillUnmount: function () {
  this.unbind();
}
render: function () {
  return (
    <div>
      { this.props.avatar &&
      <li className="list-group-item"><img src={this.props.avatar} alt={this.props.firstName} {this.props.lastName} />
      </li> }
      { this.props.firstName && this.props.lastName && <h1>{this.props.firstName} {this.props.lastName}</h1> }
    </div>
  )
}
})
;

module.exports = UserProfile;
