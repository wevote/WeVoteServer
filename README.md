[![Build Status](https://travis-ci.org/wevote/WeVoteServer.svg?branch=master)](https://travis-ci.org/wevote/WeVoteServer) [![Coverage Status](https://coveralls.io/repos/wevote/WeVoteServer/badge.svg?branch=master&service=github)](https://coveralls.io/github/wevote/WeVoteServer?branch=master)

# README for WeVoteServer

This WeVoteServer repository contains a Python/Django-powered API endpoints server. We take in ballot data from 
Google Civic API, Vote Smart, MapLight, TheUnitedStates.io and the Voting Information Project. We then serve
it up to voters, and let voters Support/Oppose and Like ballot items. We are also building tools to capture
and share voter guide data.

You can see our current alpha version for a San Francisco ballot here:
https://WeVote.US/

To get started, <a href="https://www.clahub.com/agreements/wevote/WeVoteServer">sign the Contributor License Agreement</a>.

## Installing Python/Django API Server

[Installation instructions](docs/README_API_INSTALL.md).

## Installing We Vote Mobile Web Application (Node/React/Flux)

The website front end application is powered by [WebApp](https://github.com/wevote/WebApp)

The mobile native front end applications are powered by [ReactNative for iOS and Android](https://github.com/wevote/WeVoteReactNative)


## After Installation: Working with WeVoteServer Day-to-Day

[Read about working with WeVoteServer on a daily basis](docs/README_WORKING_WITH_WE_VOTE_SERVER.md)

If you need to test donations and have not updated your openssl and pyopenssl during install and setup, you will need
[to update your local](docs/README_DONATION_SETUP.md).

## Join Us
Join our Google Group here to discuss the WeVoteServer application (creating a social ballot):
https://groups.google.com/forum/#!forum/wevoteengineering

We meet weekly on Wednesday nights at the 
[Code for San Francisco brigade of Code for America](http://www.meetup.com/Code-for-San-Francisco-Civic-Hack-Night/), 
and have mini-hackathons on many weekends. Please contact Dale.McGrew@WeVoteUSA.org for more information.

You may join our Google Group here for questions about election related data (importing and exporting):
https://groups.google.com/forum/#!forum/electiondata
