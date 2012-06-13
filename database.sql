CREATE USER tf2ib WITH PASSWORD 'jw8s0F4';
CREATE TABLE authorizations (nick varchar(255), authorized integer, level integer, time integer, admin varchar(255));
CREATE TABLE servers (dns varchar(255), ip varchar(255), last integer, port varchar(10), botID integer);
CREATE TABLE stats (class varchar(255), nick varchar(255), result integer, time integer, botID integer);
GRANT ALL PRIVILEGES ON database tf2ib TO tf2ib;
GRANT ALL PRIVILEGES ON authorizations TO tf2ib;
GRANT ALL PRIVILEGES ON servers TO tf2ib;
GRANT ALL PRIVILEGES ON stats TO tf2ib;
