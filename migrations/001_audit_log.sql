-- =====================================================================
-- CGES – ترقية 001: جدول سجل التدقيق (البند 3.7)
-- نفّذ هذا الملف مرة واحدة في Supabase > SQL Editor.
-- لا يحذف أي بيانات ولا يعدّل الجداول القائمة.
-- =====================================================================

-- جدول سجل التدقيق: من أضاف/عدّل/حذف، وأي جدول، ومتى.
-- لا يوجد مفتاح أجنبي إلى auth.users حتى لا يفشل التسجيل عند حذف مستخدم.
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  user_id uuid,
  username text,
  action text not null,          -- insert | update | delete | create_project
  table_name text not null,      -- concrete_pours | soil_receipts | ... | projects
  record_id uuid,
  project_id uuid,
  summary text,                  -- وصف مختصر مقروء للسجل
  details jsonb                  -- تفاصيل إضافية (الحقول التي تغيّرت مثلاً)
);

create index if not exists idx_audit_created on audit_log(created_at desc);
create index if not exists idx_audit_project on audit_log(project_id, created_at desc);

-- سياسات الأمان:
--   * أي مستخدم مسجَّل الدخول يكتب في السجل (لا يُسمح بالقراءة إلا للمدير).
--   * القراءة للمدير العام فقط.
alter table audit_log enable row level security;

drop policy if exists audit_insert on audit_log;
create policy audit_insert on audit_log for insert to authenticated with check (true);

drop policy if exists audit_select on audit_log;
create policy audit_select on audit_log for select using (is_admin());

grant select, insert on audit_log to authenticated;
