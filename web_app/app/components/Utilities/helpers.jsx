import axios from 'axios';

export function objectToGetParams(object) {
  return '?' + Object.keys(object)
      .filter(key => !!object[key])
      .map(key => `$key=${encodeURIComponent(object[key])}`)
      .join('&');
}

export function windowOpen(url, name, height = 400, width = 550) {
  const left = (window.outerWidth / 2)
    + (window.screenX || window.screenLeft || 0) - (width / 2);
  const top = (window.outerHeight / 2)
    + (window.screenY || window.screenTop || 0) - (height / 2);

  const config = {
    height,
    width,
    left,
    top,
    location: 'no',
    toolbar: 'no',
    status: 'no',
    directories: 'no',
    menubar: 'no',
    scrollbars: 'yes',
    resizable: 'no',
    centerscreen: 'yes',
    chrome: 'yes'
  };

  return window.open(
    url,
    name,
    Object.keys(config).map(key => `${key}=${config[key]}`).join(', ')
  );
}

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
