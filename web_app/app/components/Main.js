var React = require('react');
var RouteHandler = require('react-router').RouterHandler;
var Search = require('utilities/Search');

var Main = React.createClass({
    render: function () {
        return (
            <div className="main-container">
                <nav className="navbar navbar-default" role="navigation">
                    <div className="col-sm-7 col-sm-offset-2" style={{marginTop: 15}}>
                        <Search />
                    </div>
                </nav>
                <div className="container">
                    <RouteHandler />
                </div>
            </div>
        )
    }
});

module.exports = Main;
