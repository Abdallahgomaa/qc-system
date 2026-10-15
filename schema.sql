-- =====================================================================
-- CGES – مخطط قاعدة البيانات + سياسات الأمان (RLS)
-- نفّذه كاملاً في Supabase > SQL Editor
-- =====================================================================
create extension if not exists "pgcrypto";

-- ---------- المستخدمون والمشاريع ----------
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null,
  full_name text,
  role text not null default 'engineer' check (role in ('admin','engineer')),
  created_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  name text not null,
  client text,
  location text,
  status text not null default 'active' check (status in ('active','on_hold','closed')),
  created_at timestamptz not null default now()
);

create table if not exists project_members (
  project_id uuid references projects(id) on delete cascade,
  user_id uuid references profiles(id) on delete cascade,
  primary key (project_id, user_id)
);

-- ---------- دوال الصلاحيات ----------
create or replace function is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from profiles where id = auth.uid() and role = 'admin');
$$;

create or replace function has_project_access(pid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select is_admin() or exists (
    select 1 from project_members where project_id = pid and user_id = auth.uid());
$$;

-- ---------- الخرسانة ----------
create table if not exists concrete_pours (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  station_name text not null,
  element text not null,
  pour_date date not null,
  cubes_count int not null check (cubes_count >= 0),
  volume_m3 numeric(10,2) not null check (volume_m3 >= 0),
  design_strength_mpa numeric(6,1),
  result_7d_mpa numeric(6,1),
  result_28d_mpa numeric(6,1),
  report_7d_path text,
  report_28d_path text,
  notes text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);

-- ---------- التربة ----------
create table if not exists soil_receipts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  company text not null,
  zone text not null,
  layer_no int not null,
  level_m numeric(8,3),
  test_date date not null,
  layer_thickness_cm numeric(6,1),
  test_type text not null check (test_type in ('Dynamic','Sand Cone','Plate Load')),
  result text not null check (result in ('ناجح','ساقط')),
  report_path text,
  notes text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);

-- ---------- المواد والاختبارات الدورية ----------
create table if not exists material_tests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  material_type text not null,
  supplier text,
  test_name text not null,
  test_date date not null,
  next_test_date date,
  result text not null default 'قيد الفحص' check (result in ('مطابق','غير مطابق','قيد الفحص')),
  report_path text,
  notes text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);

-- ---------- معايرة المحطات والموازين ----------
create table if not exists station_calibrations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  station_name text not null,
  equipment_type text not null,
  serial_no text,
  last_calibration_date date not null,
  valid_until date not null,
  certificate_path text,
  notes text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);

create index if not exists idx_concrete_project on concrete_pours(project_id, pour_date);
create index if not exists idx_soil_project on soil_receipts(project_id, test_date);
create index if not exists idx_mat_project on material_tests(project_id, test_date);
create index if not exists idx_cal_project on station_calibrations(project_id, valid_until);

-- ---------- RLS ----------
alter table profiles enable row level security;
alter table projects enable row level security;
alter table project_members enable row level security;

create policy profiles_select on profiles for select using (id = auth.uid() or is_admin());
create policy profiles_admin_all on profiles for all using (is_admin()) with check (is_admin());

create policy projects_select on projects for select using (has_project_access(id));
create policy projects_admin_write on projects for all using (is_admin()) with check (is_admin());

create policy members_select on project_members for select using (user_id = auth.uid() or is_admin());
create policy members_admin_write on project_members for all using (is_admin()) with check (is_admin());

do $$
declare t text;
begin
  foreach t in array array['concrete_pours','soil_receipts','material_tests','station_calibrations']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy %I on %I for select using (has_project_access(project_id))', t||'_sel', t);
    execute format('create policy %I on %I for insert with check (has_project_access(project_id))', t||'_ins', t);
    execute format('create policy %I on %I for update using (has_project_access(project_id)) with check (has_project_access(project_id))', t||'_upd', t);
    execute format('create policy %I on %I for delete using (is_admin())', t||'_del', t);
  end loop;
end $$;

-- ---------- Storage (Bucket خاص) ----------
insert into storage.buckets (id, name, public) values ('cges-files','cges-files', false)
on conflict (id) do nothing;

-- أول مجلد في المسار = project_id
create policy cges_files_select on storage.objects for select to authenticated
  using (bucket_id = 'cges-files' and has_project_access(((storage.foldername(name))[1])::uuid));
create policy cges_files_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'cges-files' and has_project_access(((storage.foldername(name))[1])::uuid));
create policy cges_files_delete on storage.objects for delete to authenticated
  using (bucket_id = 'cges-files' and is_admin());

-- =====================================================================
-- إنشاء أول مدير عام (مرة واحدة):
-- 1) Authentication > Users > Add user: البريد admin@cges.local + كلمة مرور، وفعّل Auto Confirm
-- 2) نفّذ:
--   insert into profiles (id, username, full_name, role)
--   select id, 'admin', 'المدير العام', 'admin' from auth.users where email = 'admin@cges.local';
-- =====================================================================
