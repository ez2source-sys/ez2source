// Ez2source PWA Manager
class PWAManager {
  constructor(appType = 'candidate') {
    this.appType = appType;
    this.deferredPrompt = null;
    this.isInstalled = false;
    this.init();
  }

  init() {
    this.registerServiceWorker();
    this.setupInstallPrompt();
    this.setupMobileNavigation();
    this.checkInstallStatus();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const swPath = this.appType === 'candidate' ? '/static/sw-candidate.js' : '/static/sw-recruiter.js';
        const registration = await navigator.serviceWorker.register(swPath);
        console.log('Service Worker registered:', registration);
        
        // Request notification permission
        if ('Notification' in window && 'PushManager' in window) {
          const permission = await Notification.requestPermission();
          console.log('Notification permission:', permission);
        }
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallBanner();
    });

    window.addEventListener('appinstalled', () => {
      console.log('PWA was installed');
      this.hideInstallBanner();
      this.isInstalled = true;
    });
  }

  showInstallBanner() {
    const existingBanner = document.querySelector('.pwa-install-banner');
    if (existingBanner) return;

    const appName = this.appType === 'candidate' ? 'Ez2source Candidate' : 'Ez2source Recruiting';
    const appDesc = this.appType === 'candidate' ? 
      'Install for quick job search and applications' : 
      'Install for efficient candidate management';

    const banner = document.createElement('div');
    banner.className = 'pwa-install-banner';
    banner.innerHTML = `
      <div class="banner-content">
        <div class="banner-text">
          <div class="banner-title">${appName}</div>
          <div class="banner-subtitle">${appDesc}</div>
        </div>
        <button class="install-btn" onclick="pwaManager.installApp()">Install</button>
        <button class="close-btn" onclick="pwaManager.hideInstallBanner()">&times;</button>
      </div>
    `;

    document.body.appendChild(banner);
    setTimeout(() => banner.classList.add('show'), 100);
  }

  hideInstallBanner() {
    const banner = document.querySelector('.pwa-install-banner');
    if (banner) {
      banner.classList.remove('show');
      setTimeout(() => banner.remove(), 300);
    }
  }

  async installApp() {
    if (!this.deferredPrompt) return;

    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt');
    } else {
      console.log('User dismissed the install prompt');
    }
    
    this.deferredPrompt = null;
    this.hideInstallBanner();
  }

  setupMobileNavigation() {
    // Create mobile header if not exists
    if (!document.querySelector('.mobile-header')) {
      this.createMobileHeader();
    }

    // Setup mobile menu toggle
    this.setupMobileMenu();
    
    // Create bottom navigation for mobile
    this.createBottomNavigation();
  }

  createMobileHeader() {
    const header = document.createElement('div');
    header.className = 'mobile-header d-md-none';
    
    const appName = this.appType === 'candidate' ? 'Ez2source Candidate' : 'Ez2source Recruiting';
    
    header.innerHTML = `
      <button class="mobile-menu-btn" onclick="pwaManager.toggleMobileMenu()">
        <i data-feather="menu"></i>
      </button>
      <img src="/static/images/ez2source-logo.png" alt="${appName}" class="mobile-logo">
      <div class="mobile-user-menu">
        <button class="mobile-menu-btn" onclick="pwaManager.toggleUserMenu()">
          <i data-feather="user"></i>
        </button>
      </div>
    `;

    document.body.insertBefore(header, document.body.firstChild);
    
    // Re-render feather icons
    if (typeof feather !== 'undefined') {
      feather.replace();
    }
  }

  createBottomNavigation() {
    const existing = document.querySelector('.bottom-nav');
    if (existing) return;

    const nav = document.createElement('div');
    nav.className = `bottom-nav d-md-none ${this.appType}-app`;
    
    if (this.appType === 'candidate') {
      nav.innerHTML = `
        <a href="/dashboard" class="bottom-nav-item ${window.location.pathname.includes('dashboard') ? 'active' : ''}">
          <i data-feather="home"></i>
          <span>Dashboard</span>
        </a>
        <a href="/jobs" class="bottom-nav-item ${window.location.pathname.includes('jobs') ? 'active' : ''}">
          <i data-feather="search"></i>
          <span>Jobs</span>
        </a>
        <a href="/my-applications" class="bottom-nav-item ${window.location.pathname.includes('applications') ? 'active' : ''}">
          <i data-feather="file-text"></i>
          <span>Applications</span>
        </a>
        <a href="/candidate/edit-profile" class="bottom-nav-item ${window.location.pathname.includes('profile') ? 'active' : ''}">
          <i data-feather="user"></i>
          <span>Profile</span>
        </a>
      `;
    } else {
      nav.innerHTML = `
        <a href="/dashboard" class="bottom-nav-item ${window.location.pathname.includes('dashboard') ? 'active' : ''}">
          <i data-feather="home"></i>
          <span>Dashboard</span>
        </a>
        <a href="/candidates/universal" class="bottom-nav-item ${window.location.pathname.includes('candidates') ? 'active' : ''}">
          <i data-feather="users"></i>
          <span>Candidates</span>
        </a>
        <a href="/admin/interviews" class="bottom-nav-item ${window.location.pathname.includes('interviews') ? 'active' : ''}">
          <i data-feather="video"></i>
          <span>Interviews</span>
        </a>
        <a href="/analytics/advanced" class="bottom-nav-item ${window.location.pathname.includes('analytics') ? 'active' : ''}">
          <i data-feather="bar-chart"></i>
          <span>Analytics</span>
        </a>
      `;
    }

    document.body.appendChild(nav);
    
    // Re-render feather icons
    if (typeof feather !== 'undefined') {
      feather.replace();
    }
  }

  setupMobileMenu() {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'mobile-overlay';
    overlay.onclick = () => this.toggleMobileMenu();
    document.body.appendChild(overlay);

    // Add mobile classes to sidebar if it exists
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.classList.add('d-md-block');
    } else {
      // Create mobile navigation menu if no sidebar exists
      this.createMobileNavigationMenu();
    }
  }

  createMobileNavigationMenu() {
    // Only create if it doesn't already exist
    if (document.querySelector('.mobile-nav-menu')) return;
    
    const mobileNav = document.createElement('div');
    mobileNav.className = 'mobile-nav-menu';
    
    if (this.appType === 'candidate') {
      mobileNav.innerHTML = `
        <div class="mobile-nav-header">
          <img src="/static/images/ez2source-logo.png" alt="Ez2source" class="mobile-nav-logo">
          <button class="mobile-nav-close" onclick="pwaManager.toggleMobileMenu()">
            <i data-feather="x"></i>
          </button>
        </div>
        <div class="mobile-nav-content">
          <div class="mobile-nav-section">
            <div class="mobile-nav-label">Navigation</div>
            <a href="/dashboard" class="mobile-nav-item">
              <i data-feather="home"></i>
              <span>Dashboard</span>
            </a>
            <a href="/jobs" class="mobile-nav-item">
              <i data-feather="search"></i>
              <span>Find Jobs</span>
            </a>
            <a href="/my-applications" class="mobile-nav-item">
              <i data-feather="file-text"></i>
              <span>My Applications</span>
            </a>
            <a href="/saved-jobs" class="mobile-nav-item">
              <i data-feather="bookmark"></i>
              <span>Saved Jobs</span>
            </a>
          </div>
          <div class="mobile-nav-section">
            <div class="mobile-nav-label">Profile</div>
            <a href="/candidate/edit-profile" class="mobile-nav-item">
              <i data-feather="user"></i>
              <span>Edit Profile</span>
            </a>
            <a href="/candidate/career-readiness-journey" class="mobile-nav-item">
              <i data-feather="target"></i>
              <span>Career Journey</span>
            </a>
          </div>
          <div class="mobile-nav-section">
            <div class="mobile-nav-label">Tools</div>
            <a href="/help-center" class="mobile-nav-item">
              <i data-feather="help-circle"></i>
              <span>Help Center</span>
            </a>
            <a href="/logout" class="mobile-nav-item">
              <i data-feather="log-out"></i>
              <span>Logout</span>
            </a>
          </div>
        </div>
      `;
    } else {
      mobileNav.innerHTML = `
        <div class="mobile-nav-header">
          <img src="/static/images/ez2source-logo.png" alt="Ez2source" class="mobile-nav-logo">
          <button class="mobile-nav-close" onclick="pwaManager.toggleMobileMenu()">
            <i data-feather="x"></i>
          </button>
        </div>
        <div class="mobile-nav-content">
          <div class="mobile-nav-section">
            <div class="mobile-nav-label">Navigation</div>
            <a href="/dashboard" class="mobile-nav-item">
              <i data-feather="home"></i>
              <span>Dashboard</span>
            </a>
            <a href="/candidates/universal" class="mobile-nav-item">
              <i data-feather="users"></i>
              <span>Candidates</span>
            </a>
            <a href="/admin/interviews" class="mobile-nav-item">
              <i data-feather="video"></i>
              <span>Interviews</span>
            </a>
            <a href="/analytics/advanced" class="mobile-nav-item">
              <i data-feather="bar-chart"></i>
              <span>Analytics</span>
            </a>
          </div>
          <div class="mobile-nav-section">
            <div class="mobile-nav-label">Account</div>
            <a href="/logout" class="mobile-nav-item">
              <i data-feather="log-out"></i>
              <span>Logout</span>
            </a>
          </div>
        </div>
      `;
    }
    
    document.body.appendChild(mobileNav);
    
    // Re-render feather icons
    if (typeof feather !== 'undefined') {
      feather.replace();
    }
  }

  toggleMobileMenu() {
    console.log('toggleMobileMenu called');
    const sidebar = document.querySelector('.sidebar');
    const mobileNav = document.querySelector('.mobile-nav-menu');
    const overlay = document.querySelector('.mobile-overlay');
    
    console.log('Elements found:', { 
      sidebar: !!sidebar, 
      mobileNav: !!mobileNav, 
      overlay: !!overlay 
    });
    
    if (sidebar && overlay) {
      // Use sidebar if it exists
      console.log('Using sidebar navigation');
      sidebar.classList.toggle('show');
      overlay.classList.toggle('show');
    } else if (mobileNav && overlay) {
      // Use mobile navigation menu if no sidebar
      console.log('Using mobile navigation menu');
      mobileNav.classList.toggle('show');
      overlay.classList.toggle('show');
      document.body.classList.toggle('mobile-menu-open');
    } else {
      console.log('No sidebar or mobile nav found, creating mobile navigation');
      // Force create mobile navigation if neither exists
      this.createMobileNavigationMenu();
      const newMobileNav = document.querySelector('.mobile-nav-menu');
      const newOverlay = document.querySelector('.mobile-overlay');
      if (newMobileNav && newOverlay) {
        newMobileNav.classList.add('show');
        newOverlay.classList.add('show');
        document.body.classList.add('mobile-menu-open');
      }
    }
  }

  toggleUserMenu() {
    // Simple user menu toggle - can be enhanced
    const userMenu = document.querySelector('.dropdown-menu');
    if (userMenu) {
      userMenu.classList.toggle('show');
    }
  }

  checkInstallStatus() {
    // Check if app is installed
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      this.isInstalled = true;
      console.log('App is running in standalone mode');
    }

    // Check if app is added to home screen on iOS
    if (window.navigator.standalone === true) {
      this.isInstalled = true;
      console.log('App is running from home screen on iOS');
    }
  }

  // Push notification helpers
  async subscribeToPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.log('Push notifications not supported');
      return null;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY') // Add your VAPID key
      });

      console.log('Push notification subscription:', subscription);
      return subscription;
    } catch (error) {
      console.error('Failed to subscribe to push notifications:', error);
      return null;
    }
  }

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
}

// Initialize PWA Manager
let pwaManager;
document.addEventListener('DOMContentLoaded', () => {
  // Detect app type based on URL or user role
  const appType = window.location.pathname.includes('/candidate/') || 
                  (window.userRole && window.userRole === 'candidate') ? 'candidate' : 'recruiter';
  
  pwaManager = new PWAManager(appType);
});