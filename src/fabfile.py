# *-* coding: utf-8 -*-
import time
import sys
import os

from fabric.api import *
from fabric.contrib.files import upload_template


# Remote directory monitored by Dreamhost's passenger
env.server_site = '~/deressaca.net'
env.server_source = '~/srv'

# Set the working directory to the root of our repo,
# assuming that fabfile is on it.
os.chdir(os.path.dirname(__file__))


def deploy(**kwargs):
    """
    Deploy a given project revision to the server.
    """
    rev = kwargs.get('rev')
    if not rev:
        print 'ERROR: No revision given. Cannot deploy.'
        print 'To deploy the current revision, use the following command:'
        print '$ fab deploy:rev=`git rev-parse HEAD`'
        sys.exit(1)

    # Create a stap based on local time.
    stamp = time.strftime("%Y%m%d-%Hh%Mm%Ss")

    # Before deployment, run the tests locally.
    #local('python ./manage.py test')

    # Deploy
    _upload_project(rev, stamp)
    _activate_package(stamp)
    #server_migrate()
    server_reload()

    # Tag the deployed revision
    #local("git tag -a deploy/%s %s -m ''" % (stamp, rev))
    #local("git push --tags")


def _upload_project(rev, stamp):
    """
    Upload a specified revision to the server
    """
    require('server_source')
    package = '%s.zip' % stamp

    # Create a zip package with a specified revision.
    local('git archive --format=zip --output=%s --prefix=%s/ %s' % \
        (package, stamp, rev))

    # Put the package on the server.
    server_package = os.path.join(env.server_source, package)
    put(package, server_package)

    # Unpack it on the server.
    with cd(env.server_source):
        run('unzip %s' % stamp)
        run('rm %s' % server_package)

    # Delete the local zip file
    local('rm %s' % package)


def _activate_package(stamp):
    """
    Set the server symlink to a specific uploaded package.
    """
    require('server_site', 'server_source')
    run('rm -f %(server_site)s' % env)
    stamp_source = os.path.join(env.server_source, stamp)
    run('ln -s %s %s' % (stamp_source, env.server_site))
    run('rm -f %(server_site)s/project/local_settings.py' % env)
    run('ln -s %(server_source)s/local_settings.py %(server_site)s/local_settings.py' % env)
    run('ln -s %(server_source)s/deressaca.db %(server_site)s/deressaca.db' % env)


def server_migrate():
    """
    Run syncdb and migrate command on the server
    """
    require('server_site')
    with cd(env.server_site):
        run("""
            PYTHONPATH=%s/src:%s/lib:%s && \
            python manage.py syncdb --noinput && python manage.py migrate
            """ % (env.server_site,) * 3 )


def server_reload():
    """
    Reload Dreamhost's webserver to avoid cache problems.
    """
    run('pkill python')
