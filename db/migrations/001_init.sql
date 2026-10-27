-- Dupuytren's & Ledderhose specialist directory.
-- Listings are rebuilt from data/build/directory.json on every seed; patient submissions are never touched by seeding.

create extension if not exists pg_trgm;

create table if not exists sources (
  id            text primary key,
  label         text not null,
  url           text not null,
  kind          text not null,            -- patient_org_list | registry | community | literature
  page_modified date
);

create table if not exists treatments (
  code  text primary key,
  label text not null
);

create table if not exists providers (
  id                 text primary key,     -- stable slug, e.g. "gary-pess-eatontown"
  kind               text not null check (kind in ('clinician', 'practice', 'trial_site')),
  name               text not null,
  honorific          text,
  credential         text,
  specialty          text,
  specialty_label    text,
  colleagues         text[] not null default '{}',
  website            text,
  websites           text[] not null default '{}',
  emails             text[] not null default '{}',
  conditions         text[] not null default '{}',   -- dupuytren | ledderhose
  countries          text[] not null default '{}',
  flags              text[] not null default '{}',   -- early_stage, nhs, private, video_consult, rt_referral, ...
  early_stage        boolean not null default false,
  verification_level text not null check (verification_level in ('corroborated', 'listed', 'needs_review')),
  verification       jsonb not null,                 -- {level, reasons[], warnings[], checked}
  npi                jsonb,
  publications       jsonb,
  reddit             jsonb,
  trials             jsonb not null default '[]',
  notes              jsonb not null default '[]',
  source_refs        jsonb not null default '[]',
  mention_count      integer not null default 0,
  search_text        text not null default '',
  updated_at         timestamptz not null default now()
);
create index if not exists providers_search_trgm on providers using gin (search_text gin_trgm_ops);
create index if not exists providers_conditions on providers using gin (conditions);
create index if not exists providers_countries on providers using gin (countries);

create table if not exists locations (
  id            serial primary key,
  provider_id   text not null references providers(id) on delete cascade,
  position      integer not null,
  practice      text,
  street        text,
  city          text,
  region        text,
  postal        text,
  country       text not null,
  phone         text,
  lat           double precision,
  lng           double precision,
  geo_precision text,                     -- street | postal | city | region | practice
  from_npi      boolean not null default false
);
create index if not exists locations_provider on locations(provider_id);
create index if not exists locations_latlng on locations(lat, lng);

create table if not exists provider_treatments (
  provider_id text not null references providers(id) on delete cascade,
  code        text not null references treatments(code),
  site        text not null check (site in ('hand', 'foot')),
  best        text not null check (best in ('listed', 'trial_site', 'trial_investigator', 'patient_reported', 'inferred')),
  evidence    jsonb not null,
  primary key (provider_id, code, site)
);
create index if not exists provider_treatments_code on provider_treatments(code, site, best);

create table if not exists provider_sources (
  provider_id text not null references providers(id) on delete cascade,
  source_id   text not null references sources(id),
  primary key (provider_id, source_id)
);

create table if not exists trials (
  nct_id     text primary key,
  status     text not null,
  site       text not null,               -- hand | foot (condition studied)
  data       jsonb not null,
  updated_at timestamptz not null default now()
);

-- Patient submissions: new providers, corrections, and treatment experiences. Moderated before anything is published.
create table if not exists submissions (
  id          bigserial primary key,
  kind        text not null check (kind in ('new_provider', 'correction', 'experience')),
  provider_id text,                       -- not a FK: listings are rebuilt on every seed
  payload     jsonb not null,
  contact     text,
  status      text not null default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  created_at  timestamptz not null default now(),
  ip_hash     text
);
create index if not exists submissions_status on submissions(status, created_at);

create table if not exists geocode_cache (
  query      text primary key,
  result     jsonb,
  created_at timestamptz not null default now()
);

create table if not exists schema_migrations (
  name       text primary key,
  applied_at timestamptz not null default now()
);
