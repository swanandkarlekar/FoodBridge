/**
 * FoodBridge - Main Interactive Vanilla JS Script
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Toggle
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      const isExpanded = navLinks.classList.contains('open');
      navToggle.setAttribute('aria-expanded', isExpanded);
    });
  }

  // 2. Flash Alert Auto-Dismiss & Close Buttons
  const alertCloseButtons = document.querySelectorAll('.alert-close');
  alertCloseButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        alert.style.transition = 'all 0.25s ease';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });

  // Auto-dismiss success and info alerts after 6 seconds
  const autoAlerts = document.querySelectorAll('.alert-success, .alert-info');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      if (document.body.contains(alert)) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        alert.style.transition = 'all 0.3s ease';
        setTimeout(() => alert.remove(), 300);
      }
    }, 6000);
  });

  // 3. Demo Credentials Autofill Helper
  window.fillDemoCredentials = function(email, password) {
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    if (emailInput && passwordInput) {
      emailInput.value = email;
      passwordInput.value = password;
      emailInput.focus();
      // Add slight highlight pulse
      emailInput.style.backgroundColor = '#ecfdf5';
      passwordInput.style.backgroundColor = '#ecfdf5';
      setTimeout(() => {
        emailInput.style.backgroundColor = '';
        passwordInput.style.backgroundColor = '';
      }, 500);
    }
  };

  // 4. Admin Dashboard Tabs
  const tabButtons = document.querySelectorAll('.admin-tab-btn');
  const tabPanes = document.querySelectorAll('.admin-tab-pane');
  if (tabButtons.length > 0 && tabPanes.length > 0) {
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTab = button.dataset.tab;
        
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));

        button.classList.add('active');
        const activePane = document.getElementById(`tab-${targetTab}`);
        if (activePane) {
          activePane.classList.add('active');
        }
      });
    });
  }

  // 5. Request Donation Modal Logic
  const openModalBtn = document.getElementById('open-request-modal');
  const closeModalBtn = document.getElementById('close-request-modal');
  const requestModal = document.getElementById('request-modal');

  if (openModalBtn && requestModal) {
    openModalBtn.addEventListener('click', () => {
      requestModal.style.display = 'flex';
    });
  }

  if (closeModalBtn && requestModal) {
    closeModalBtn.addEventListener('click', () => {
      requestModal.style.display = 'none';
    });
  }

  // Close modal when clicking outside content
  if (requestModal) {
    requestModal.addEventListener('click', (e) => {
      if (e.target === requestModal) {
        requestModal.style.display = 'none';
      }
    });
  }

  // 6. Generic Form Confirmation Prompts
  const confirmForms = document.querySelectorAll('form[data-confirm]');
  confirmForms.forEach(form => {
    form.addEventListener('submit', (e) => {
      const message = form.dataset.confirm || 'Are you sure you want to perform this action?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });
});
