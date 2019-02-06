# README for API Installation

[Back to root README](../README.md)

## Installing WeVoteServer: Native development

Please note: We do not support direct development on Windows.
If you are using a Windows machine, we recommend setting up an [Oracle VirtualBox](https://www.virtualbox.org/wiki/Downloads)
and installing within that. In our experience, a Windows machine should have 8 GB RAM (minimum),
and you should allocate 2 CPUs and 4 GB RAM to the virtual machine.

1a. [Installing PostgreSQL on Mac](README_API_INSTALL_POSTGRES_MAC.md)

1b. [Installing PostgreSQL on Linux](README_API_INSTALL_POSTGRES_LINUX.md)

2. [Get WeVoteServer Code from Github](README_API_INSTALL_CODE_FROM_GITHUB.md)

3a. [Install Python/Django on Mac](README_API_INSTALL_PYTHON_MAC.md)

3b. [Install Python/Django on Linux](README_API_INSTALL_PYTHON_LINUX.md)

4. [Set up Environment](README_API_INSTALL_SETUP_ENVIRONMENT.md)

5. [Set up Database](README_API_INSTALL_SETUP_DATABASE.md)

6. [Set up Initial Data](README_API_INSTALL_SETUP_DATA.md)

[Troubleshooting](README_INSTALLATION_TROUBLESHOOTING.md)

[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to root README](../README.md)

## Installing WeVoteServer: Vagrant and Ansible

You can build WeVoteServer as a Vagrant box using our
[Ansible-Vagrant project](https://github.com/wevote/ansible-django-stack).
Note that Ansible is straightforward to install on Mac and Linux hosts, but
Windows isn't supported by Ansible. You may try to
[install via Cygwin](https://www.jeffgeerling.com/blog/running-ansible-within-windows),
or for Windows 10 or later,
[install via the Windows 10 subsystem](https://www.jeffgeerling.com/blog/2017/using-ansible-through-windows-10s-subsystem-linux),
at which point you should be able to proceed with the Ansible-Vagrant
instructions.

Alternatively, you can try the prebuilt Vagrant box, which lets you avoid Ansible setup entirely. [Using the prebuilt Vagrant box](README_API_INSTALL_VAGRANT_PREBUILT.md)

## Installing on Amazon Web Services (For network team only)

[AWS Notes](README_API_INSTALL_AWS.md)

## Maintaining Django Code Tests

[Django Code Tests](README_DJANGO_TESTS.md)