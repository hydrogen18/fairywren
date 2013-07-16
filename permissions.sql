GRANT all on torrents to webapi;
GRANT UPDATE,SELECT on torrents_id_seq to webapi;
GRANT ALL on users to webapi;
GRANT UPATE,SELECT on users_id_seq to webapi;

GRANT SELECT on torrents to tracker;
GRANT SELECT on users to tracker;
