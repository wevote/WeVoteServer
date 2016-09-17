# loadtest
This is a [Locust] script to load test WeVote server API.
### Usage
First [install Locust].
Then run the default test by executing:
```
$ loadtest/load.sh
```

If you want to use a specific voter_device_id for your test,
cp loadtest/test_variables_template.json loadtest/test_variables.json
and set the voter_device_id there
[//]: #
[Locust]: <http://locust.io>
[install Locust]: <http://docs.locust.io/en/latest/installation.html>
