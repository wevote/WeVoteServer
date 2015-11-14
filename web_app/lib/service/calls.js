'use strict';
var axios = require('axios');
var api = require('./api');

module.exports = (function () {
    // basic error handling function...
    function err (res) {
        new Error("Request failed with " + res.status + ": " + res.text)
    }

    function get ( endpoint, params, cb ) {
        // get the api endpoint
        let _endpoint = api(endpoint);
        let method = _endpoint.method;

        // move callback to second argument
        if (typeof params === 'function') { cb = params; }

        // do nothing, correct input
        else if ( typeof params === 'object' && typeof cb === 'function' ) {}

        // throw an error, the function was called incorrectly...
        else {
            throw new Error('incorrect parameters');
            return null;
        }

        // if endpoint requires parameters then verify that they are correct
        if ( _endpoint.parameters.length > 0 ) {
            // verify all the required parameters exist on function call
            Object.keys(params).forEach( (key) => {
                if ( _endpoint.parameters.indexOf(key) < 0 ) {
                    throw new Error('missing required parameter key' + key);
                    return null;
                }
            });

            // return the axios call
            return axios[method](_endpoint.path, params).catch(err).then(cb);

        } else {
            // return the axios call with no params
            return axios[method](_endpoint.path).catch(err).then(cb);
        }
    }
    // main call function
    return {
        get: get,
        post: get //alias for get
    }

}());
