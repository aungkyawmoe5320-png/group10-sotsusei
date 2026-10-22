// Service worker: the browser runs this file in the background

// 1) A push message arrived from our server
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { body: event.data ? event.data.text() : "" };
  }

  const title = data.title || "みまもりケアリング";
  const options = {
    body: data.body || "予定の時間です",
    tag: data.tag,                       // same tag = replace the old notification
    vibrate: data.vibrate || undefined,  // e.g. [200, 100, 200] (Android only)
    data: { url: data.url || "/schedule/" },
  };

  // waitUntil keeps the worker alive until the notification is shown
  event.waitUntil(self.registration.showNotification(title, options));
});

// 2) The user tapped the notification: open the schedule page
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});