var axios = require('axios');

function getUserProfile(username) {
  return axios.get('http://localhost:8000/users/' + username + '/');
}

var helpers = {
    getUserInfo: function(username) {
      // axios.all returns array of promises
      return axios.all([getUserProfile(username)])
        .then(function(arr) {
          return {
            username: arr[0].data
          }
        })
    }
};

module.exports = helpers;
