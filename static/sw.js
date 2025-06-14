const CACHE_NAME = 'carpet-invoices-v1';
const urlsToCache = [
  '/',
  '/static/tailwind.css',
  '/static/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/htmx.org@1.9.10',
  'https://unpkg.com/feather-icons'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }
        
        return fetch(event.request).then(function(response) {
          // Check if we received a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          var responseToCache = response.clone();

          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(function() {
          // If both cache and network fail, show offline page for navigation requests
          if (event.request.destination === 'document') {
            return caches.match('/offline.html');
          }
        });
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for offline data submission
self.addEventListener('sync', function(event) {
  if (event.tag === 'invoice-sync') {
    event.waitUntil(syncInvoices());
  }
});

async function syncInvoices() {
  try {
    // Get pending invoices from IndexedDB
    const pendingInvoices = await getPendingInvoices();
    
    for (const invoice of pendingInvoices) {
      try {
        const response = await fetch('/api/sync-invoice', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(invoice)
        });
        
        if (response.ok) {
          // Remove from pending list
          await removePendingInvoice(invoice.id);
          console.log('Synced invoice:', invoice.id);
        }
      } catch (error) {
        console.error('Failed to sync invoice:', invoice.id, error);
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// IndexedDB helpers for offline storage
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('CarpetInvoicesDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = () => {
      const db = request.result;
      
      if (!db.objectStoreNames.contains('pendingInvoices')) {
        const store = db.createObjectStore('pendingInvoices', { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

async function getPendingInvoices() {
  const db = await openDB();
  const transaction = db.transaction(['pendingInvoices'], 'readonly');
  const store = transaction.objectStore('pendingInvoices');
  
  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function addPendingInvoice(invoice) {
  const db = await openDB();
  const transaction = db.transaction(['pendingInvoices'], 'readwrite');
  const store = transaction.objectStore('pendingInvoices');
  
  invoice.timestamp = Date.now();
  
  return new Promise((resolve, reject) => {
    const request = store.add(invoice);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function removePendingInvoice(invoiceId) {
  const db = await openDB();
  const transaction = db.transaction(['pendingInvoices'], 'readwrite');
  const store = transaction.objectStore('pendingInvoices');
  
  return new Promise((resolve, reject) => {
    const request = store.delete(invoiceId);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

// Push notification handling
self.addEventListener('push', function(event) {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icon-192x192.png',
      badge: '/static/badge-72x72.png',
      tag: 'carpet-invoices',
      requireInteraction: true,
      actions: [
        {
          action: 'view',
          title: 'View Invoice'
        },
        {
          action: 'dismiss',
          title: 'Dismiss'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handling for communication with main thread
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_INVOICE') {
    cacheInvoiceData(event.data.invoice);
  }
});

async function cacheInvoiceData(invoice) {
  try {
    await addPendingInvoice(invoice);
    console.log('Invoice cached for offline sync:', invoice.id);
    
    // Register for background sync
    self.registration.sync.register('invoice-sync');
  } catch (error) {
    console.error('Failed to cache invoice:', error);
  }
}

// Network status change handling
self.addEventListener('online', function() {
  console.log('App is online, attempting to sync pending data');
  self.registration.sync.register('invoice-sync');
});

self.addEventListener('offline', function() {
  console.log('App is offline, caching enabled');
});
