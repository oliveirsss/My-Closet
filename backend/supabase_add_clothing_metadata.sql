alter table public.clothes
  add column if not exists color text,
  add column if not exists style text,
  add column if not exists occasion text;

update public.clothes
set
  color = nullif(lower(trim(color)), ''),
  style = nullif(lower(trim(style)), ''),
  occasion = nullif(lower(trim(occasion)), '')
where color is not null
   or style is not null
   or occasion is not null;

notify pgrst, 'reload schema';
