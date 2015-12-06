var model = require('./model.js');

// The logged in users deviceid

// basic error handling function...
function err (res) {
    new Error("Request failed with " + res.status + ": " + res.text);
}

// get the data from an endpoint
// NOTE: the endpoints are mapped in model.js
function get ( endpoint, params, cb ) {
    var _endpoint = model(endpoint);
    var method = _endpoint.method;

    // move callback to second argument
    if (typeof params === 'function') { cb = params; }

    // do nothing, correct input
    else if ( typeof params === 'object' && typeof cb === 'function' ) {}

    // throw an error, the function was called incorrectly...
    else {
        throw new Error('incorrect parameters');
    }

    // if endpoint requires parameters then verify that they are correct
    if ( _endpoint.parameters.length > 0 ) {
        // verify all the required parameters exist on function call
        Object.keys(params).forEach( (key) => {
            if ( _endpoint.parameters.indexOf(key) < 0 ) {
                throw new Error('missing required parameter key' + key);
            }
        });
    }

    // return the axios call
    return axios[method](_endpoint.path, params || {})
        .catch(err)
        .then((res) => cb(res.data, res));

}

/**
 * deviceIdGenerate -> generate a device id
 * for the logged in user if one does not exist
 * @return {bool} success value of true | false
 */
export function deviceIdGenerate () {
    var key = 'voter_device_id';

    return new Promise((resolve, reject) => {
        if (device_id === null) {
            get(
                'deviceIdGenerate',
                (data) => {
                    device_id = data[key];
                    cookies.setItem(key, device_id);
                }
            ).then(() => {
                var params = {};
                params[key]=device_id;

                get(
                    'voterCreate',
                    params,
                    (data) => {
                        if(data.success) resolve(data[key]);
                        else reject(data);
                    }
                );
            });
        }
    }).catch(err);
};

/**
 * voterCount -> gets the voter count
 * @return {Promise} that will resolve when the voter count is retreived from the server
 */
export function voterCount () {
    return new Promise((resolve, reject) => {
        get ('voterCount', (data) => {
            if(data.success) resolve(data.voter_count);
            else reject(data);
        });
    }).catch(err);
};

export function organizationCount () {
    return new Promise((resolve, reject) => {
        get ('organizationCount', (data) => {
            if(data.success) resolve(data.organization_count);
            else reject(data);
        });
    }).catch(err);
}
