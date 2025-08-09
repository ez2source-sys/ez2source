// EZ2Hire Recruiting App Service Worker
const CACHE_NAME = 'ez2hire-recruiter-v1.0';
const urlsToCache = [
  '/admin/dashboard',
  '/admin/candidates',
  '/admin/interviews',
  '/admin/analytics',
  '/static/css/mobile-responsive.css',
  '/static/css/light-theme.css',
  '/static/js/mobile-optimizations.js',
  '/static/images/ez2source-logo.png'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Return cached version or fetch from network
        return response || fetch(event.request);
      }
    )
  );
});

// Handle push notifications for recruiters
self.addEventListener('push', function(event) {
  const options = {
    body: event.data ? event.data.text() : 'New candidate application received!',
    icon: '/static/images/ez2source-logo.png',
    badge: '/static/images/ez2source-logo.png',
    tag: 'application-notification',
    actions: [
      {
        action: 'view',
        title: 'View Applications'
      },
      {
        action: 'dismiss', 
        title: 'Dismiss'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('EZ2Hire Recruiting', options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/admin/applications')
    );
  }
});