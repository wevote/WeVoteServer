# loadtest
This is a [Locust] script to load test WeVote server API.
### Usage
First [install Locust].
Then run the default test by executing this from the WeVoteServer folder:
```
$ loadtest/load.sh
```

Make sure you have installed locustio:

```
$ pip install locustio
```

You will want to use a specific voter_device_id for your test. To get a current voter_device_id, visit https://WeVote.US and copy the voter_device_id from any of the API calls:

Then paste it in "loadtest/test_variables.json".

```
cp loadtest/test_variables_template.json loadtest/test_variables.json
```

[//]: #
[Locust]: <http://locust.io>
[install Locust]: <http://docs.locust.io/en/latest/installation.html>
