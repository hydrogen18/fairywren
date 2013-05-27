CREATE TABLE users(
	id serial UNIQUE,
	name varchar NOT NULL UNIQUE,
	password char(86),
	secretKey char(86),
	PRIMARY KEY(id,name)
);

CREATE TABLE torrents(
	id SERIAL UNIQUE,
	infoHash char(27) NOT NULL UNIQUE,
	title varchar(128) NOT NULL,
	creator INTEGER REFERENCES users(id) NOT NULL,
	creationDate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY(id,infoHash)
);
	
	
