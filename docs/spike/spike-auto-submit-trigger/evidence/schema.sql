-- Non-destructive setup only. Use the guarded probe.ps1 for a destructive reset.
-- This file intentionally targets a dedicated local database.
USE sp03_probe;

CREATE TABLE papers (
  id         VARCHAR(36) NOT NULL PRIMARY KEY,
  status     VARCHAR(16) NOT NULL,
  start_at   DATETIME(3) NOT NULL,
  end_at     DATETIME(3) NOT NULL,
  created_by VARCHAR(36) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE answer_sheets (
  id           VARCHAR(36) NOT NULL PRIMARY KEY,
  paper_id     VARCHAR(36) NOT NULL,
  student_id   VARCHAR(36) NOT NULL,
  status       VARCHAR(16) NOT NULL,
  started_at   DATETIME(3) NOT NULL,
  submitted_at DATETIME(3) NULL,
  submit_type  VARCHAR(8) NULL,
  UNIQUE KEY uk_answer_sheet_paper_student (paper_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE answer_items (
  answer_sheet_id VARCHAR(36) NOT NULL,
  question_id     VARCHAR(36) NOT NULL,
  content         MEDIUMTEXT NOT NULL,
  saved_at        DATETIME(3) NOT NULL,
  PRIMARY KEY (answer_sheet_id, question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
