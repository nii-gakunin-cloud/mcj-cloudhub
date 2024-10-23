CREATE TABLE IF NOT EXISTS log
(id                        INTEGER     NOT NULL,
 assignment                VARCHAR     NOT NULL,
 student_id                VARCHAR     NOT NULL,
 log_id                    VARCHAR     NOT NULL,
 log_sequence              INTEGER     NOT NULL,
 notebook_name             VARCHAR,
 log_whole                 JSON,
 log_code                  VARCHAR,
 log_path                  VARCHAR,
 log_start                 TIMESTAMP,
 log_end                   TIMESTAMP,
 log_size                  INTEGER,
 log_server_signature      VARCHAR,
 log_uid                   INTEGER,
 log_gid                   INTEGER,
 log_notebook_path         VARCHAR,
 log_lc_notebook_meme      VARCHAR,
 log_execute_reply_status  VARCHAR,
 PRIMARY KEY (id),
 CONSTRAINT UC_log UNIQUE (assignment, student_id, log_id, log_sequence)
);
CREATE TABLE IF NOT EXISTS log_id
(id                        VARCHAR     NOT NULL,
 assignment                VARCHAR     NOT NULL,
 section                   VARCHAR,
 notebook_name             VARCHAR,
 CONSTRAINT UC_log UNIQUE (id, assignment)
);
CREATE TABLE IF NOT EXISTS student
(id                        VARCHAR     NOT NULL,
 PRIMARY KEY (id)
);
