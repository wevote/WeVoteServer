# Starting from the prebuilt Vagrant box

[Back to Install Table of Contents](README_API_INSTALL.md)

[Installation Troubleshooting](README_INSTALLATION_TROUBLESHOOTING.md)

# Introduction

Try this method if you want to develop on WeVoteServer locally, can use [Vagrant](https://www.vagrantup.com/) with [VirtualBox](https://www.vagrantup.com/docs/providers/) on your local machine, and don't want to or can't run Ansible host (this is especially for Windows users).

You'll end up with a prebuilt Vagrant box that's the same as if you have built the [We Vote Ansible/Django/Vagrant project](https://github.com/wevote/ansible-django-stack) from scratch. For further documentation on what's installed, see [that project's README](https://github.com/wevote/ansible-django-stack#ansible-django-stack).

Following these instructions, you will

- Check out the WeVoteServer codebase to a directory
- Create a Vagrant directory at the same level
- Download a prebuilt Vagrant box and Vagrantfile
- Import and start the Vagrant box
- Continue with the WeVoteServer setup instructions

## Clone application code base

`git clone` the [WeVoteServer project](https://github.com/wevote/WeVoteServer) (or your fork of it). We're going to assume that this lives at `/path/to/WeVoteServer`.

## Create a parent directory for Vagrant

Create a directory at `/path/to/WeVote-Vagrant`. The name isn't important, but the location is: this setup assumes it's in the same parent directory as the WeVoteServer code base.

## Download the Vagrant box

Download [the prebuilt Vagrant box](https://www.dropbox.com/s/7lxmf3yvkjmd0yo/wevote-server.latest.box?dl=1) to `/path/to/WeVote-Vagrant`.

Download [the Vagrantfile](https://gist.githubusercontent.com/mshmsh5000/515d9deababf60ac00258055ba7d4905/raw/286d051408238133dd30c7274a1110060a69348b/Vagrantfile) to the same directory.

## Import and start the Vagrant box

You'll only need to import the box the first time you run it. From `/path/to/WeVote-Vagrant`, run

`vagrant box add --name wevote-imported wevote-server.latest.box`

When that is done, you can start as you normally do:

`vagrant up`

## Continue with the WeVoteServer setup instructions

You should start with [this Django env vars file](https://gist.githubusercontent.com/mshmsh5000/70ff7b7a615b50ed938ed2003a7a2f04/raw/772f588c54ac7799cb2f2eb702faab68bc3b8b1a/environmental-variables.json). It's missing secrets and other API keys for service integrations, but it will enable the Django app to start and run. Copy the file to `WeVoteServer/config/environment_variables.json`.

After this, restart the Django app so that it reloads these variables. To do this:

1. From `/path/to/WeVote-Vagrant`, run `vagrant ssh`. This logs you into the Vagrant box.
2. Run `sudo supervisorctl restart wevoteserver`. This forces Gunicorn, the app server, to restart.

Note the URL specified for the API server in those env vars: https://localhost:8889/ Try this after you restart Gunicorn.

From here, you should be able to continue with the [app setup instructions](https://github.com/wevote/WeVoteServer/blob/develop/docs/README_API_INSTALL_SETUP_DATABASE.md#grant-yourself-admin-rights).

## Running the Django CLI

The application directory `WeVoteServer` that's mounted from your host machine into Vagrant will be owned by the `ubuntu` user. So, when you want to run Django commands such as `migrate`, you'll need to do that (a) as `ubuntu` and (b) within the `virtualenv`. To do this:

1. From the directory containing your Vagrantfile: `vagrant ssh`
2. Now you're logged in to the Vagrant box as the `ubuntu` user.
3. `cd /webapps/wevoteserver`
4. `. bin/activate` to activate the `virtualenv`
5. `cd WeVoteServer`

Now you're the `ubuntu` user, within `virtualenv`, and in the root application directory. From here, you can run commands such as

- `./manage.py makemigrations`
- `./manage.py migrate`

And so on.

This is a test.
