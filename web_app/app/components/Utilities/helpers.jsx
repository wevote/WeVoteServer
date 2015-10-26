import axios from 'axios';

function getUserProfile(username) {
  return axios.get(`http://localhost:8000/users/${username}/`);
}

const helpers = {
  getUserInfo(username) {
    // axios.all returns array of promises
    return axios.all([getUserProfile(username)])
      .then((arr) => {
        return {
          username: arr[0].data
        };
      });
  }
};

export default helpers;
