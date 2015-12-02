import React, { Component } from 'react';
import { Router, Route, IndexRoute } from 'react-router';

// main Application
import Application  						from 'Application';


/****************************** ROUTE-COMPONENTS ******************************/
import MyBallot							    from 'route-components/MyBallot';
import Requests                             from 'route-components/Requests';
import Connect                              from 'route-components/Connect';
import About                                from 'route-components/About';
import Activity                             from 'route-components/Activity';
import More                                 from 'route-components/More';
import Donate								from 'route-components/Donate';


// polyfill
if (!Object.assign) Object.assign = React.__spread;

export default class Root extends Component {
    static propTypes = {
        history: React.PropTypes.object.isRequired
    };

    render() {
        const {history} = this.props;

        return (
            <Router history={history}>
                <Route name='app' path='/' component={Application}>
                    <IndexRoute component={MyBallot} />
                    <Route name='myballot' path='myballot' component={MyBallot} />
                    <Route name='requests' path='requests' component={Requests} />
                    <Route name='more' path='more' component={More} />
                    <Route name='activity' path='activity' component={Activity} />
                    <Route name='connect' path='connect' component={Connect} />
                    <Route name='about' path='about' component={About} />
                    <Route name='donate' path='donate' component={Donate} />
                </Route>
            </Router>
        );
    }
};
