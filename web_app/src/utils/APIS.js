/**
 * The idea of this APIS.js file is to abstract away the details
 * of many repetitive service calls that we will be using.
 *
 * Our models will be callable VIA an import.
 * so it should work like this:
 *     import { voterCount } from utils/APIS;
 *
 *     voterCount().then(data => setDeviceId(data.device_id))
 */

'use strict';

const axios = require('axios');

// basic endpoint url configuration
const protocol = 'http://';
const host = 'localhost';
const port = ':8000';
const base_path = '/apis/v1/';

// full url to API endpoints
let url = `${protocol}${host}${port}${base_path}`;

function checkParams(params, params_in) {
    if (!params instanceof Array)
        throw new Error('params must be array');

    var keys = Object.keys(params_in);

    if (params.length !== keys.length)
        return false; // params not valid

    return keys.every( key => {
        var index = params.indexOf(key);
        return index >= 0 ? params.splice(index, 1) : false;
    })
}

module.exports = {
    /********** Voter Basic Data **********/
    deviceIdGenerate: () => axios.get(url + 'deviceIdGenerate'),
    voterAddressRetrieve: () => axios.get(url + 'voterAddressRetrieve'),
    voterAddressSave: params => {
        if (checkParams(['api_key', 'voter_device_id', 'address'], params))
            return axios.post(url + 'voterAddressSave', params);
        else
            throw new Error('incorrect parameters', params);
    },
    voterCount: () => axios.get(url + 'voterCount'),
    voterCreate: voter_device_id => {
        const params = { voter_device_id };
        if (checkParams(['voter_device_id'], params))
            return axios.get(url + 'voterCreate', params);
        else
            throw new Error('missing voter_device_id', params);
    },
    voterRetrieve: voter_device_id => {
        const params = { voter_device_id };
        if (checkParams(['voter_device_id'], params))
            return axios.get(url + 'voterRetrieve', params);
        else
            throw new Error('missing voter_device_id', params);
    },

    /********** Org, People & Voter Guides **********/
    organizationCount: () => axios.get(url + 'organizationCount'),


    /********** Ballot Contest Data **********/
    ballotItemOptionsRetrieve: params => {
        if (checkParams(['voter_device_id', 'api_key'], params))
            return axios.get(url + 'ballotItemOptionsRetrieve', params);
        else
            throw new Error('incorrect parameters', params);
    },

    electionsRetrieve:  params => {
        if (checkParams(['voter_device_id', 'api_key'], params))
            return axios.get(url + 'electionsRetrieve', params);
        else
            throw new Error('incorrect parameters', params);
    },

    voterBallotItemsRetrieve: params => {
        if (checkParams(['voter_device_id', 'api_key'], params))
            return axios.get(url + 'voterBallotItemsRetrieve', params);
        else
            throw new Error('incorrect parameters', params);
    },

    /********** Candidates & Measures **********/
    candidatesRetrieve: office_we_vote_id => {
        var params = { office_we_vote_id };
        if (checkParams(['office_we_vote_id'], params))
            return axios.get(url + 'candidatesRetrieve', params);
        else
            throw new Error('missing office_we_vote_id parameter', params);

    }

};
