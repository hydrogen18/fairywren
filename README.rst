=====
Fairywren
=====

Introduction
=======

Fairywren is a private bittorrent tracker written around postgresql and
eventlet . At this stage it is still very simple.

Software Dependencies
=======

To run fairywren you'll need the following 

.. _Stackless: http://stackless.com/wiki/Download 
.. _Eventlet: http://eventlet.net
.. _Psycopg2: https://pypi.python.org/pypi/psycopg2 
.. _Multipart: https://github.com/hydrogen18/multipart
.. _ZeroMq: http://www.zeromq.org/area%3Adownload
.. _pyzmq: http://www.zeromq.org/bindings%3Apython
.. _GDBM: http://www.gnu.org.ua/software/gdbm/
- Stackless_
- Eventlet_
- Psycopg2_
- Multipart_
- ZeroMq_
- pyzmq_ 
- GDBM
- Postgresql
- A web server that supports proxying. I use lighttpd.


The unit tests also require

.. _wsgi-intercept: https://pypi.python.org/pypi/wsgi_intercept

- wsgi-intercept_

Architecture
=======

HTTP
------
Two seperate Python instances are launched. Each hosts a single HTTP
server. One instance is the tracker, which is used by BitTorrent clients
to exchange peers. The second is the web interface, which is a RESTful API
for interacting with the private tracker. The HTML5 & JavaScript
web interface is best served by a traditional web server.

Each instance is ran behind a HTTPS server(lighttpd in my case) which
proxies requests to them. 

SQL
----
The PostgreSQL server is used by both instances. The tracker uses it
to authorize specific torrents and users. Peers are stored only in memory.
The web server uses it to allow users to login and upload new torrents.

The tables needed are specified in fairywren.sql. The roles needed
are in roles.sql. The permissions for the roles are granted in permissions.sql.

Two users are used in my configuration, a read only user for the tracker
and a read-write user for the webapi. The example roles and permissions
are shown in roles.sql and permissions.sql. Obviously, a single user
with global permissions could be substituted.

Object Store
----
The uploaded BitTorrent files are pickled and stored in a gdbm database.
For the moment, it seems to be an appropriate solution. If you have performance problems,
feel free to let me know.

Configuration
=======

The configuration file is a JSON file which configures both the tracker
and the API. The basic outline is shown in example.conf.json. The JSON
file is a dictionary. The keys are 

trackerUrl
    The external URL that the web server proxies to the tracker
    
pathDepth
    An integer specifying the depth at which the API and the tracker are proxied from. This is
    used to allow the code to be independent of the website it is hosted
    on. For example the URL http://a.com/b/d/f/api/torrents with this
    configuration value set to 4 causes the first four parts of the path
    to be ignored and just 'torrents' to be matched against when processing
    the request.
    
salt
    A string used to salt users password before storing them in the database.
    This value should be random, long, and guarded as secret. Changing this
    value after adding users is equivalent to setting all users passwords to 
    random values.
    
.. _webapi:
webapi
    Configuration values specific to the API. See webapi_.
    
.. _tracker:
tracker
    Configuration values specific to the tracker. See the tracker_.
    
    
tracker
------

postgresql
    A dictionary of values. These are passed to the constructor of
    psycopg2.connect verbatim
    
webapi
------

postgresql
    A dictionary of values. These are passed to the constructor of
    psycopg2.connect verbatim

torrentPath
    A string which is the path GDBM file. Fairywren stores uploaded
    BitTorrent files in this database. If the file does not exist it will be
    created.

secure
    A boolean indicating if sesssion cookies issued should be flagged
    with the 'Secure' option. Used when running behind an HTTPS proxy.
    
Adding users
====
Presently, users cannot be added via the web interface. The script
adduser.py takes a single argument which is the same JSON configuration
file as used by the HTTP servers. It prompts for the username
and password to add. All users have the same permissions presently.
    

