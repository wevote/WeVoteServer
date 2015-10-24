import React from 'react';
const RouteHandler = require('react-router').RouterHandler;
import Search from 'utilities/Search';

const Main = React.createClass({
  render() {
    return (<div className="main-container">
        <nav className="navbar navbar-default" role="navigation">
            <div className="col-sm-7 col-sm-offset-2" style={{marginTop: 15}}>
                <Search />
            </div>
        </nav>
        <div className="container">
            <RouteHandler />
        </div>
    </div>
    );
  }
});

module.exports = Main;
