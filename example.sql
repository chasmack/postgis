
create view v as
select *
from ( values ('foo', 2),
              ('foo', 3),
              ('foo', 4),
              ('foo', 10),
              ('foo', 11),
              ('foo', 13),
              ('bar', 1),
              ('bar', 2),
              ('bar', 3)
     ) as baz (name, int);


with recursive t(name, int) as (
  select name, int, 1 as span from v
  union all
    select name, v.int, t.span+1 as span
      from v join t using (name)
      where v.int=t.int+1
)
select name, start, start + span - 1 as end, span
from (
  select name, (int - span + 1) as start, max(span) as span
  from (
    select name, int, max(span) as span
    from t
    group by name, int ) z
  group by name, (int - span + 1) ) z;

