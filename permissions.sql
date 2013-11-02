GRANT all on torrents to webapi;
GRANT UPDATE,SELECT on torrents_id_seq to webapi;
GRANT ALL on users to webapi;
GRANT UPdATE,SELECT on users_id_seq to webapi;
GRANT ALL on roles to webapi;
GRANT UPDATE,SELECT on roles_id_seq to webapi;
GRANT ALL on rolemember to webapi;
GRANT ALL on invites to webapi;
GRANT UPDATE,SELECT on invites_id_seq to webapi;
GRANT ALL ON peers to webapi;

GRANT SELECT on torrents to tracker;
GRANT SELECT on users to tracker;
GRANT ALL on peers to tracker;

