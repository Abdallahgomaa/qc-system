/* CGES — Service Worker (البندان أ و ب).
 *
 * تنبيه مهم: Streamlit يقدّم هذا الملف من /app/static/، ونطاق أي Service Worker
 * محصور بمجلد ملفه، لذلك نطاقه هنا /app/static/ فقط ولا يستطيع التحكم بالصفحة
 * الرئيسية على Streamlit Community Cloud (لا يُرسل الترويسة
 * Service-Worker-Allowed: /). الفائدة العملية: تخزين صفحة «العرض بدون اتصال»
 * والأيقونات، فتفتح بدون شبكة وتقرأ آخر لقطة محفوظة في المتصفح.
 */
const CACHE = "cges-offline-v1";
const ASSETS = [
  "/app/static/offline.html",
  "/app/static/field.html",
  "/app/static/manifest.webmanifest",
  "/app/static/icon-192.png",
  "/app/static/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (!url.pathname.startsWith("/app/static/")) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        return res;
      })
      .catch(() =>
        caches.match(e.request).then((hit) => hit || caches.match("/app/static/offline.html"))
      )
  );
});
