/**
 * Service Worker for Job2Hire
 * Provides offline caching and performance optimizations
 */

const CACHE_NAME = 'job2hire-v1.0.0';
const OFFLINE_URL = '/offline.html';

const CACHE_URLS = [
    '/',
    '/static/css/style.css',
    '/static/css/mobile-responsive.css',
    '/static/css/light-theme.css',
    '/static/css/accessibility-improvements.css',
    '/static/js/mobile-optimizations.js',
    '/static/js/form-validation.js',
    '/static/images/logos/job2hire_logo_small.png',
    '/static/images/logos/job2hire_logo_medium.png',
    '/static/images/logos/job2hire_logo_large.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://unpkg.com/feather-icons'
];

// Install event
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Caching critical resources');
                return cache.addAll(CACHE_URLS.map(url => new Request(url, {
                    cache: 'reload'
                })));
            })
            .catch(error => {
                console.error('Cache installation failed:', error);
            })
    );
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event
self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    // Return cached version
                    return response;
                }
                
                // Network first for dynamic content
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Cache successful responses
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(() => {
                        // Return offline page for navigation requests
                        if (event.request.destination === 'document') {
                            return caches.match(OFFLINE_URL);
                        }
                        
                        // Return cached response or fallback
                        return caches.match(event.request);
                    });
            })
    );
});

// Background sync
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(
            // Implement background sync logic here
            console.log('Background sync triggered')
        );
    }
});

// Push notifications
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/images/logos/job2hire_logo_medium.png',
            badge: '/static/images/logos/job2hire_logo_small.png',
            vibrate: [100, 50, 100],
            data: {
                dateOfArrival: Date.now(),
                primaryKey: data.primaryKey
            }
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Notification click
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow('/dashboard')
    );
});