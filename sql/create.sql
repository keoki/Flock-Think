CREATE DATABSE insight;
USE insight;
CREATE TABLE querylogs
(
	query_id SERIAL,
	search_term varchar(1000), -- twitter limits queries to < 1000 char
	time DATETIME,
	num_pos int,
	num_neg int,
	num_neu int, -- neutral
	PRIMARY KEY (query_id)
);

CREATE TABLE tweets
(
	query_id BIGINT UNSIGNED NOT NULL,
	tweet_id BIGINT UNSIGNED NOT NULL,
	twitter_id BIGINT UNSIGNED NOT NULL,
	sentiment FLOAT, -- number between [0:1]. 0 = negative, 1 = positive.
	FOREIGN KEY (query_id) REFERENCES querylogs(query_id)
);

