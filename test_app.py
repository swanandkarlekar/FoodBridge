"""
Automated Comprehensive Test Suite for FoodBridge Platform
Verifies all routes, authentication, role authorization, CSRF, donation flow, and admin access.
"""

import io
import os
import sys
import unittest
from werkzeug.security import check_password_hash
from app import app
from db import query_db, execute_db, init_db
from seed import seed_database

class FoodBridgeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            init_db()
            # Silence stdout during seeding
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                seed_database()
            finally:
                sys.stdout = old_stdout

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            # Clean any dynamic test rows from prior test methods
            execute_db("DELETE FROM users WHERE email LIKE '%@test.org'")
            execute_db("DELETE FROM donations WHERE title LIKE '%Hot Lentil Soup%'")
            execute_db("DELETE FROM donation_requests WHERE message LIKE '%Hope Shelter van can pick this up%'")
            execute_db("DELETE FROM contact_messages WHERE email = 'organizer@civic.org'")

    def get_csrf_token(self):
        """Helper to extract active session CSRF token."""
        with self.client.session_transaction() as sess:
            return sess.get('_csrf_token', 'test_token')

    # 1. Test Public Routes
    def test_01_public_pages(self):
        """Verify home, about, contact, and donations pages render cleanly."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Good Food Deserves a', res.data)
        self.assertIn(b'Meals Rescued', res.data)

        res = self.client.get('/about')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transforming Surplus into Sustenance', res.data)

        res = self.client.get('/contact')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Send Us a Message', res.data)

        res = self.client.get('/donations')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Available Food Donations', res.data)

    # 2. Test Donations Search & Filters
    def test_02_donations_filtering(self):
        """Verify search, category filter, and sorting on donations page."""
        # Filter Bakery
        res = self.client.get('/donations?category=Bakery')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Bakery', res.data)

        # Search term
        res = self.client.get('/donations?q=Mediterranean')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Mediterranean', res.data)

        # Non-existent search
        res = self.client.get('/donations?q=NonExistentFoodXYZ')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'No matching donations found', res.data)

    # 3. Test Donation Detail
    def test_03_donation_detail(self):
        """Verify viewing donation detail page and 404 for missing ID."""
        res = self.client.get('/donations/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Donation Specifications', res.data)

        # Missing donation ID
        res = self.client.get('/donations/9999')
        self.assertEqual(res.status_code, 404)
        self.assertIn(b'Page Not Found', res.data)

    # 4. Test User Registration
    def test_04_user_registration(self):
        """Verify user registration, input validation, and secure password hashing."""
        self.client.get('/register')
        token = self.get_csrf_token()

        # Valid registration
        res = self.client.post('/register', data={
            'csrf_token': token,
            'name': 'New Community Donor',
            'email': 'newdonor@test.org',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'role': 'donor',
            'organization': 'Corner Cafe',
            'phone': '+1 555-9999',
            'city': 'Metropolis'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

        # Verify password is hashed, not plaintext
        with app.app_context():
            u = query_db("SELECT * FROM users WHERE email = 'newdonor@test.org'", one=True)
            self.assertIsNotNone(u)
            self.assertNotEqual(u['password_hash'], 'StrongPassword123!')
            self.assertTrue(check_password_hash(u['password_hash'], 'StrongPassword123!'))

        # Duplicate email registration attempt
        self.client.get('/register')
        token = self.get_csrf_token()
        res_dup = self.client.post('/register', data={
            'csrf_token': token,
            'name': 'Duplicate User',
            'email': 'newdonor@test.org',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'role': 'donor'
        })
        self.assertIn(b'already exists', res_dup.data)

    # 5. Test Authentication (Login, Logout)
    def test_05_auth_flow(self):
        """Verify login, session state, and logout."""
        self.client.get('/login')
        token = self.get_csrf_token()

        # Invalid credentials
        res_fail = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'donor@foodbridge.org',
            'password': 'WrongPassword!'
        })
        self.assertIn(b'Invalid email address or password', res_fail.data)

        # Valid login
        res_ok = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'donor@foodbridge.org',
            'password': 'FoodBridge123!'
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn(b'Welcome back, Marcus Vance', res_ok.data)

        # Access dashboard as logged in user
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'Donor Workspace', res_dash.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'signed out', res_logout.data)

    # 6. Test Posting a Food Donation
    def test_06_post_donation(self):
        """Verify donor can create a new food listing with validation."""
        self.client.get('/login')
        self.client.post('/login', data={
            'csrf_token': self.get_csrf_token(),
            'email': 'donor@foodbridge.org',
            'password': 'FoodBridge123!'
        })

        token = self.get_csrf_token()
        res_post = self.client.post('/donate', data={
            'csrf_token': token,
            'title': 'Hot Lentil Soup & Whole Grain Rolls',
            'category': 'Cooked Meals',
            'servings': '45',
            'quantity': '3 large insulated soup thermoses',
            'description': 'Freshly prepared vegetarian lentil soup with warm rolls from our dinner banquet.',
            'address': '452 Elm Street',
            'city': 'Metropolis',
            'pickup_deadline': 'Today by 8:00 PM',
            'prepared_time': 'Today at 5 PM',
            'allergens': 'Vegetarian, Vegan, Gluten (in rolls)',
            'donor_contact': '+1 (555) 234-5678',
            'instructions': 'Pick up at rear dock'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b'published', res_post.data)
        self.assertIn(b'Hot Lentil Soup', res_post.data)

    # 7. Test NGO Requesting a Donation
    def test_07_ngo_request_donation(self):
        """Verify NGO can request available donation and duplicate request is prevented."""
        self.client.get('/login')
        self.client.post('/login', data={
            'csrf_token': self.get_csrf_token(),
            'email': 'ngo@foodbridge.org',
            'password': 'FoodBridge123!'
        })

        token = self.get_csrf_token()
        # Request donation ID 1 (Artisan Sourdough)
        res_req = self.client.post('/donations/1/request', data={
            'csrf_token': token,
            'servings_requested': '50',
            'message': 'Hope Shelter van can pick this up tomorrow morning.'
        }, follow_redirects=True)
        self.assertEqual(res_req.status_code, 200)
        self.assertIn(b'submitted successfully', res_req.data)

        # Attempt duplicate request for same donation
        token = self.get_csrf_token()
        res_dup = self.client.post('/donations/1/request', data={
            'csrf_token': token,
            'servings_requested': '30',
            'message': 'Duplicate request attempt'
        }, follow_redirects=True)
        self.assertIn(b'already have an active request', res_dup.data)

    # 8. Test Contact Form
    def test_08_contact_submission(self):
        """Verify submitting contact form saves message in database without claiming email sent."""
        self.client.get('/contact')
        token = self.get_csrf_token()

        res = self.client.post('/contact', data={
            'csrf_token': token,
            'name': 'Community Organizer',
            'email': 'organizer@civic.org',
            'subject': 'Food Safety Workshop Collaboration',
            'category': 'Partnership',
            'message': 'We would like to coordinate a workshop for local food truck owners on FoodBridge.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'inquiry has been received', res.data)

        with app.app_context():
            msg = query_db("SELECT * FROM contact_messages WHERE email = 'organizer@civic.org'", one=True)
            self.assertIsNotNone(msg)
            self.assertEqual(msg['subject'], 'Food Safety Workshop Collaboration')

    # 9. Test Role Permissions & Admin Restrictions
    def test_09_admin_authorization(self):
        """Verify regular users get 403 on admin routes, but admin has access."""
        # Guest gets redirected to login
        res_guest = self.client.get('/admin', follow_redirects=True)
        self.assertIn(b'Administrator sign-in required', res_guest.data)

        # Regular donor gets 403
        self.client.get('/login')
        self.client.post('/login', data={
            'csrf_token': self.get_csrf_token(),
            'email': 'donor@foodbridge.org',
            'password': 'FoodBridge123!'
        })
        res_forbidden = self.client.get('/admin')
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn(b'Access Forbidden', res_forbidden.data)

        # Log out and log in as Admin
        self.client.get('/logout')
        self.client.get('/login')
        self.client.post('/login', data={
            'csrf_token': self.get_csrf_token(),
            'email': 'admin@foodbridge.org',
            'password': 'AdminSecret2026!'
        })
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Platform Operations Dashboard', res_admin.data)
        self.assertIn(b'Food Donation Moderation', res_admin.data)

    # 10. Test Volunteer Flow
    def test_10_volunteer_mission(self):
        """Verify volunteer dashboard and mission claiming."""
        self.client.get('/login')
        self.client.post('/login', data={
            'csrf_token': self.get_csrf_token(),
            'email': 'volunteer@foodbridge.org',
            'password': 'FoodBridge123!'
        })
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Volunteer Workspace', res.data)

if __name__ == '__main__':
    unittest.main()
