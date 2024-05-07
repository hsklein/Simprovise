PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

DROP TABLE IF EXISTS simdata;
DROP TABLE IF EXISTS dataset;


CREATE TABLE timeunit(
	  id INTEGER PRIMARY KEY
	, name TEXT NOT NULL UNIQUE
	, abbrev TEXT NOT NULL UNIQUE
	, tosecsMultiplier INTEGER NOT NULL
);

INSERT INTO timeunit VALUES(-1, 'None', 'n/a', 0);
INSERT INTO timeunit VALUES(0, 'Seconds', 'secs', 1);
INSERT INTO timeunit VALUES(1, 'Minutes', 'mins', 60);
INSERT INTO timeunit VALUES(2, 'Hours', 'hrs', 3600);


CREATE TABLE elementtype(
	  id INTEGER PRIMARY KEY
	, name TEXT NOT NULL UNIQUE
);
INSERT INTO elementtype VALUES(1, 'Process');
INSERT INTO elementtype VALUES(2, 'Resource');
INSERT INTO elementtype VALUES(3, 'Location');
INSERT INTO elementtype VALUES(4, 'Source');
INSERT INTO elementtype VALUES(5, 'Sink');
INSERT INTO elementtype VALUES(6, 'Entity');


CREATE TABLE element(
	  id TEXT PRIMARY KEY 
	, classname TEXT NOT NULL
	, type INTEGER NOT NULL REFERENCES elementtype(id) ON DELETE RESTRICT ON UPDATE CASCADE
) WITHOUT ROWID;

CREATE VIEW elementview as
select element.id as id, elementtype.name as type, element.classname as class
	FROM  element INNER JOIN elementtype ON element.type = elementtype.id;



CREATE TABLE dataset(
	  id INTEGER PRIMARY KEY AUTOINCREMENT
	, element TEXT NOT NULL REFERENCES element(id) ON DELETE CASCADE ON UPDATE CASCADE
	, name TEXT NOT NULL
	, valueType TEXT NOT NULL
	, istimeweighted BOOLEAN 
	, timeunit INTEGER NOT NULL REFERENCES timeunit(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE UNIQUE INDEX dataset_idx ON dataset(element, name);

CREATE TABLE datasetvalue(
	  dataset INTEGER NOT NULL REFERENCES dataset(id) ON DELETE CASCADE ON UPDATE CASCADE
	, run INTEGER NOT NULL CHECK (run > 0)
	, batch INTEGER NOT NULL CHECK (batch >= 0)
	, simtimestamp NUMERIC NOT NULL
	, totimestamp NUMERIC 
	, value NUMERIC NOT NULL 
);
CREATE INDEX datasetvalue_idx on datasetvalue (run, batch, dataset);
