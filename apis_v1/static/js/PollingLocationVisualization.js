// apis_v1/static/js/PollingLocationVisualization.js
// Draw a Google Map, and overlay it with the Polling Locations.

let map;
let state = '';
let stateHtml = '';
let infoWindow;
const markers = [];
const { $ } = window;

// https://developers.google.com/maps/documentation/javascript/tutorial
// https://developers.google.com/maps/documentation/javascript/markers
// https://developers.google.com/maps/documentation/javascript/custom-markers
// https://developers.google.com/maps/solutions/store-locator/clothing-store-locator

function createSelect () {
  const stateListString = $('#state_list').val();
  // "[('AK', 'Alaska'), ('AL', 'Alabama'), ('AR', 'Arkansas')
  const regex = /(\(.*?\))/gm;
  const matches = Array.from(stateListString.matchAll(regex));
  let selectComponent = "<span>Select a state: <select id='state_code' name='state_code'>";
  for (let i = 0; i < matches.length; i++) {
    const match = matches[i][0];                      // "('AL', 'Alabama')"
    const matchStateCode = match.substring(2, 4);
    if (matchStateCode !== 'NA') {
      const matchStateLong = match.substring(8, match.length - 2);
      const selected = matchStateCode === state ? ' selected=\'selected\'' : '';
      selectComponent += `<option value='${matchStateCode}' ${selected} >${matchStateLong}</option>`;      // <option value='AK'>Alaska</option>
    }
  }
  selectComponent += '</select></span>';
  $(selectComponent).insertBefore('#map');

  $('select').change(() => {
    const selectedState = $('select option:selected').val();   // "PA"
    let { href } = window.location;
    const n = href.lastIndexOf('=') + 1;
    href = href.substring(0, n) + selectedState;
    window.location.href = href;
  });
}


function setStateVariable () {
  const href1 = window.location.href;
  const stateURL = href1.substring(href1.length - 2);
  if (stateHtml.length !== 2) {
    stateHtml = $('#state_code').val();
  }
  state = (stateURL.lastIndexOf('=') < 0) ? stateURL : stateHtml;
}

function createMarker (latlng, name, address) {
  const html = `<b>${name}</b> <br/>${address}`;
  const marker = new google.maps.Marker({
    position: latlng,
    icon: 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png',
    map,
  });

  google.maps.event.addListener(marker, 'click', () => {
    infoWindow.setContent(html);
    infoWindow.open(map, marker);
  });
  markers.push(marker);
}

function addMarkers (results) {
  // Create markers.
  for (let i = 0; i < results.length; i++) {
    const { latitude, longitude, location_name: locationName, line1, city, state: resultsState, we_vote_id: weVoteId,
      id: pollingLocTableId  } = results[i];
    let { href } = window.location;
    href = `${href.substring(0, href.lastIndexOf('/pl/') + 4) + pollingLocTableId}/summary/`;
    const link = `<a href='${href}' target='_blank'>Open ${weVoteId}</a>`;
    const address = `${line1}, ${city} ${resultsState}<br/>${link}`;
    createMarker(new google.maps.LatLng(latitude, longitude), locationName, address);
  }
}

// See https://developers.google.com/maps/solutions/store-locator/clothing-store-locator
// for a nicer way to do this, call it on initialization of page, instead of from
// google.maps.api inclusion.  Low priority.
window.initMap = () => {
  const geoLat = parseInt($('#geo_center_lat').val());
  const geoLng = parseInt($('#geo_center_lng').val());
  const geoZoom = parseInt($('#geo_center_zoom').val());
  const myLatLng = { lat: geoLat, lng: geoLng };

  map = new google.maps.Map(document.getElementById('map'), {
    center: myLatLng,
    zoom: geoZoom,
  });
  const mapdiv = $('#map');
  mapdiv.css('width', '100%');
  mapdiv.css('height', '800');
  mapdiv.css('border', 'thin solid black');

  infoWindow = new google.maps.InfoWindow();

  if (state.length < 2) {
    setStateVariable();
  }

  const newTaskData = {
    state,
  };

  const apiURL = `${window.location.origin}/apis/v1/pollingLocationsSyncOut`;
  $.getJSON(apiURL, newTaskData, (results) => { addMarkers(results); })
    .fail((err) => {
      console.log('error', err);
    });
};

$(() => {
  const theMap = $('#map');
  stateHtml = $('#state_code').val();

  setStateVariable();

  const targetHeight = window.innerHeight - 150;
  theMap.css({
    width: '100%',
    height: targetHeight,
    border: 'thin solid black',
    'margin-top': '10px',
  });

  createSelect();
});
