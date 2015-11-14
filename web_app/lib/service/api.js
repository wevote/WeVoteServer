// basic endpoint url configuration
var host = 'http://localhost';
var port = ':8000';
var base = '/apis/v1/';
var url = host + port + base

module.exports = function (endpoint) {
    switch (endpoint) {
        case 'deviceIdGenerate':
            return {
                method: 'get',
                parameters: [],
                path: url + 'deviceIdGenerate'
            }
        case 'voterCount':
            return {
                method: 'get',
                parameters: [],
                path: url + 'voterCount'
            }
        case 'voterCreate':
            return {
                method: 'get',
                parameters: ['voter_device_id'],
                path: url + 'voterCreate'
            }
        default:
            throw new Error('endpoint ' + endpoint + ' does not exist');
    }
};
