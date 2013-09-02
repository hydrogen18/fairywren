=====
Fairywren
=====

Fairywren is a private BitTorrent tracker written around Postgresql and
Eventlet.

Features
=======

- Upload torrents through web interface
- Search for torrents by title
- View number of seeders and leechers in real time
- Create one time invites to send to new users
- HTML5 & Javascript written using Bootstrap, displays well on phones and tablets
- Backend of web interface is entirely RESTful

Screenshots
=====

Browsing and creating torrents
-------

.. image :: screenshots/torrents.png

.. image :: screenshots/upload.png

.. image :: screenshots/search.png

Inviting new users
-------

.. image :: screenshots/invites.png

.. image :: screenshots/register.png

Software Dependencies
=======

To run fairywren you'll need the following 

.. _Stackless: http://stackless.com/wiki/Download 
.. _Eventlet: http://eventlet.net
.. _Psycopg2: https://pypi.python.org/pypi/psycopg2 
.. _Multipart: https://github.com/hydrogen18/multipart
.. _ZeroMq: http://www.zeromq.org/area%3Adownload
.. _pyzmq: http://www.zeromq.org/bindings%3Apython
- Stackless_
- Eventlet_
- Psycopg2_
- Multipart_
- ZeroMq_
- pyzmq_ 
- Postgresql
- A web server that supports proxying. I use lighttpd.


The unit tests also require

.. _wsgi-intercept: https://pypi.python.org/pypi/wsgi_intercept

- wsgi-intercept_

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

secure
    A boolean indicating if sesssion cookies issued should be flagged
    with the 'Secure' option. Used when running behind an HTTPS proxy.
    
Adding users
====
The script adduser.py takes a single argument which is the same JSON configuration
file as used by the HTTP servers. Please note you must run this script after
you have have launched standalone_webapi.py at least once. There is a small
amount of bootstrapping that has to on before users can be created.

You are prompted for the username and password of the newly created user.
Users created with this script have permission to
create invites. Creating invites, which are one time user hyperlinks,
and sending them to new users is the preferred method for adding
new users after the first user is created. Eventually, I'll get around to
creating a web interface to add and remove permissions from users.


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

IPC
---

In order to display the seeders and leechers count on each torrent, the 
web interface needs to get those counts from the tracker. This is done
by having the tracker listen on a ZeroMQ PubSub connection. The web interface
connects to this as a subscriber. Each time the peer count changes on 
a torrent, the tracker publishes an update to the web interface. The web
interface maintains a list of counts in memory in order to serve them
with each request for torrent listings.

SQL
----
The PostgreSQL server is used by both server instances. 

The tracker uses the database to authorize specific torrents and users.
There is no writing to the database by the tracker. Peers are stored only in memory.
At first this seems silly, but given that there is rarely a reason to restart
the tracker it works well. If the tracker is restarted, it only takes
until all peers have announce'd to rebuild the complete list of peers. If
someone comes up with a use case where the tracker is consuming too
much memory, the intent will be to move the peer lists into a Redis
instance. 

The web server uses it to allow users to login and upload new torrents.
Torrents themselves are completely stored in the database. The actual
uploaded BitTorrent files are decoded from their bencoded form, then pickled and stored in the gdbm databse. Any
extended information for a torrent is stored as a pickled object as well.
Initially, I was lead to believe this is a bad idea. I learned that PostgreSQL
implements TOAST which allows large entries to be stored outside of the row
they are part of. This mitigates the performance impact if the entry is seldom
accessed. For now this is an appropriate solution. If scalability becomes
an issue, I will move to implementing a LRU type cache in the application.

The tables needed are specified in fairywren.sql. The roles needed
are in roles.sql. The permissions for the roles are granted in permissions.sql.

Two users are used in my configuration, a read only user for the tracker
and a read-write user for the webapi. The example roles and permissions
are shown in roles.sql and permissions.sql. Obviously, a single user
with global permissions could be substituted.



    

