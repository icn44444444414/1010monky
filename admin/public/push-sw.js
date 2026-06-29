/* 1010monky admin – push service worker. Tar emot push och visar notis. */
self.addEventListener('push', function (event) {
  var data = { title: '1010monky', body: 'Nytt meddelande', url: '/admin/inkorg' };
  try { if (event.data) { data = Object.assign(data, event.data.json()); } } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/admin/images/favicon.svg',
      badge: '/admin/images/favicon.svg',
      tag: 'monky-chat',
      renotify: true,
      data: { url: data.url || '/admin/inkorg' }
    })
  );
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/admin/inkorg';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].url.indexOf('/admin') > -1 && 'focus' in list[i]) { return list[i].focus(); }
      }
      if (self.clients.openWindow) { return self.clients.openWindow(url); }
    })
  );
});
