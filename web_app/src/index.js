import React from 'react';
import ReactDOM from 'react-dom';
import { createHistory } from 'history';
import Root from './Root.jsx';

const rootEl = document.getElementById('app');


const history = createHistory();

ReactDOM.render(<Root history={history} />, rootEl);
