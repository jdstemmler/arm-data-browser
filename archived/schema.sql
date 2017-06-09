drop table if exists cases;
create table cases (
  id integer primary key autoincrement,
  date_submitted text not null,
  case_date text not null,
  description text not null,
  category text,
  name text,
  email text
);
