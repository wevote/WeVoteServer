var React = require('react');

var Profiles = React.createClass({
  propTypes: {
    profiles: React.PropTypes.array
  },

  render: function () {
    var profiles = this.props.profiles.map((profile. index) => {
      return (
        <li className="list-group-item" key={index}>
          {profile.firstName && <p> {profile.firstName}</p>}
        </li>
      );
    });
    return (
      <div className="well">
        <p>{profiles}</p>
      </div>
    )
  }
})
