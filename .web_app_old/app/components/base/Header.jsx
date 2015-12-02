import React from "react";

require("stylesheets/bootstrap.3.3.1.min");

class Header extends React.Component {
  render() {
    return (
      <section className="navbar navbar-default">
        <h2>{this.props.title}</h2>
        <section>{this.props.children}</section>
      </section>
    );
  }
};

React.render(<Header />, document.getElementById('content'));
