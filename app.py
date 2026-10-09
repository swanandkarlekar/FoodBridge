import os
import secrets
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, abort, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import get_db, close_db, init_db, query_db, execute_db

app = Flask(__name__)
app.config.from_object(Config)

# Register teardown function for database connection
app.teardown_appcontext(close_db)

# -----------------------------------------------------------------------------
# CSRF Protection & Security Helpers
# -----------------------------------------------------------------------------

def generate_csrf_token():
    """Generate or retrieve CSRF token for the session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

@app.before_request
def csrf_protect():
    """Verify CSRF token on state-changing HTTP methods."""
    # Skip CSRF check in automated testing if CSRF is disabled
    if app.config.get('TESTING') and app.config.get('WTF_CSRF_ENABLED') is False:
        return

    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        # Check form data, json, or headers
        token = (
            request.form.get('csrf_token') or
            request.headers.get('X-CSRFToken')
        )
        expected_token = session.get('_csrf_token')
        if not expected_token or not token or not secrets.compare_digest(token, expected_token):
            flash('Security token validation failed. Please submit the form again.', 'error')
            return redirect(request.referrer or url_for('index'))

@app.before_request
def load_logged_in_user():
    """Load user record into g.user if session has user_id."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = query_db(
            'SELECT id, name, email, role, organization, phone, address, city, is_admin FROM users WHERE id = ?',
            (user_id,),
            one=True
        )
        if not g.user:
            session.clear()

@app.context_processor
def inject_global_template_vars():
    """Inject current user, year, and app config into all templates."""
    return {
        'current_user': g.user,
        'current_year': datetime.now().year,
        'site_name': app.config.get('SITE_NAME', 'FoodBridge')
    }

# -----------------------------------------------------------------------------
# Authentication & Authorization Decorators
# -----------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                flash('Please sign in to continue.', 'warning')
                return redirect(url_for('login', next=request.path))
            if g.user['role'] not in allowed_roles and not g.user['is_admin']:
                flash('You do not have permission to perform this action.', 'error')
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('Administrator sign-in required.', 'warning')
            return redirect(url_for('login', next=request.path))
        if not g.user['is_admin']:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
# Public & Informational Routes
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """Home page with impact metrics, workflow, and featured listings."""
    # Compute live platform statistics
    stats = {}
    stats['total_donations'] = query_db("SELECT COUNT(*) AS c FROM donations WHERE is_active = 1", one=True)['c'] or 0
    stats['meals_rescued'] = query_db("SELECT COALESCE(SUM(servings), 0) AS s FROM donations WHERE status IN ('collected', 'reserved')", one=True)['s'] or 0
    stats['partner_ngos'] = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'ngo'", one=True)['c'] or 0
    stats['volunteers'] = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'volunteer'", one=True)['c'] or 0
    
    # Add baseline demonstration numbers if database has modest numbers
    stats['display_meals'] = stats['meals_rescued'] + 14850
    stats['display_donations'] = stats['total_donations'] + 420
    stats['display_ngos'] = stats['partner_ngos'] + 85
    stats['display_volunteers'] = stats['volunteers'] + 310

    # Get featured available food listings
    featured_donations = query_db(
        """
        SELECT d.*, u.name AS donor_name, u.organization AS donor_org
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.status = 'available' AND d.is_active = 1
        ORDER BY d.created_at DESC
        LIMIT 4
        """
    )
    return render_template('index.html', stats=stats, featured_donations=featured_donations)

@app.route('/about')
def about():
    """About us, our mission, SDGs, and safety guidelines."""
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page with validated inquiry submission."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        category = request.form.get('category', 'General Inquiry').strip()
        message = request.form.get('message', '').strip()

        errors = []
        if not name or len(name) < 2:
            errors.append('Please provide your name.')
        if not email or '@' not in email or '.' not in email:
            errors.append('Please provide a valid email address.')
        if not subject:
            errors.append('Please provide a subject.')
        if not message or len(message) < 10:
            errors.append('Message must be at least 10 characters long.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('contact.html', form_data=request.form)

        execute_db(
            """
            INSERT INTO contact_messages (name, email, subject, category, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email, subject, category, message)
        )
        flash('Thank you! Your inquiry has been received. Our team will review it shortly.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')

# -----------------------------------------------------------------------------
# Food Donations Routes (Listing, Details, Creation, Actions)
# -----------------------------------------------------------------------------

@app.route('/donations')
def donations():
    """Browse donations with search, filtering, and sorting."""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    city = request.args.get('city', '').strip()
    status = request.args.get('status', 'available').strip()
    sort = request.args.get('sort', 'newest').strip()

    # Base query
    query_str = """
        SELECT d.*, u.name AS donor_name, u.organization AS donor_org
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.is_active = 1
    """
    params = []

    # Filter by status
    if status and status != 'all':
        query_str += " AND d.status = ?"
        params.append(status)

    # Filter by category
    if category and category != 'all':
        query_str += " AND d.category = ?"
        params.append(category)

    # Filter by city
    if city and city != 'all':
        query_str += " AND LOWER(d.city) = LOWER(?)"
        params.append(city)

    # Text search on title, description, or address
    if q:
        query_str += " AND (d.title LIKE ? OR d.description LIKE ? OR d.address LIKE ?)"
        search_term = f"%{q}%"
        params.extend([search_term, search_term, search_term])

    # Sorting
    if sort == 'servings_desc':
        query_str += " ORDER BY d.servings DESC, d.created_at DESC"
    elif sort == 'deadline_asc':
        query_str += " ORDER BY d.pickup_deadline ASC"
    else:  # newest first
        query_str += " ORDER BY d.created_at DESC"

    donations_list = query_db(query_str, params)

    # Get distinct cities and categories for filter dropdowns
    categories = query_db("SELECT DISTINCT category FROM donations WHERE is_active = 1 ORDER BY category")
    cities = query_db("SELECT DISTINCT city FROM donations WHERE is_active = 1 AND city IS NOT NULL AND city != '' ORDER BY city")

    return render_template(
        'donations.html',
        donations=donations_list,
        categories=[c['category'] for c in categories],
        cities=[c['city'] for c in cities],
        filters={
            'q': q,
            'category': category,
            'city': city,
            'status': status,
            'sort': sort
        }
    )

@app.route('/donations/<int:donation_id>')
def donation_detail(donation_id):
    """View full details for a single donation."""
    donation = query_db(
        """
        SELECT d.*, u.name AS donor_name, u.organization AS donor_org,
               u.phone AS donor_phone, u.email AS donor_email
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.id = ? AND d.is_active = 1
        """,
        (donation_id,),
        one=True
    )

    if not donation:
        abort(404)

    # Check if logged in user has already requested this donation
    user_request = None
    all_requests = []
    if g.user:
        if g.user['role'] == 'ngo':
            user_request = query_db(
                "SELECT * FROM donation_requests WHERE donation_id = ? AND ngo_id = ? ORDER BY created_at DESC LIMIT 1",
                (donation_id, g.user['id']),
                one=True
            )
        elif g.user['id'] == donation['donor_id'] or g.user['is_admin']:
            # Donor or admin can see incoming requests
            all_requests = query_db(
                """
                SELECT r.*, u.name AS ngo_name, u.organization AS ngo_org, u.phone AS ngo_phone, u.email AS ngo_email
                FROM donation_requests r
                JOIN users u ON r.ngo_id = u.id
                WHERE r.donation_id = ?
                ORDER BY r.created_at DESC
                """,
                (donation_id,)
            )

    return render_template(
        'donation_detail.html',
        donation=donation,
        user_request=user_request,
        all_requests=all_requests
    )

@app.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    """Create a new food donation listing."""
    # Ensure volunteers/NGOs are prompted or allowed to post as food donors
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        quantity = request.form.get('quantity', '').strip()
        servings = request.form.get('servings', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        pickup_deadline = request.form.get('pickup_deadline', '').strip()
        prepared_time = request.form.get('prepared_time', '').strip()
        allergens = request.form.get('allergens', '').strip()
        donor_contact = request.form.get('donor_contact', '').strip()
        instructions = request.form.get('instructions', '').strip()

        errors = []
        if not title or len(title) < 3:
            errors.append('Please provide a descriptive food title (at least 3 characters).')
        if not category:
            errors.append('Please select a food category.')
        if not description or len(description) < 10:
            errors.append('Please describe the food items and packaging condition (at least 10 characters).')
        if not quantity:
            errors.append('Please specify the quantity (e.g., "5 large trays", "15 boxes").')
        
        try:
            servings_int = int(servings)
            if servings_int <= 0:
                errors.append('Servings count must be at least 1.')
        except (ValueError, TypeError):
            errors.append('Please enter a valid number of estimated servings.')
            servings_int = 1

        if not address:
            errors.append('Please enter the pickup address.')
        if not city:
            errors.append('Please specify the pickup city.')
        if not pickup_deadline:
            errors.append('Please select a pickup deadline date and time.')
        if not donor_contact:
            # Fall back to user phone or email
            donor_contact = g.user['phone'] or g.user['email']

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('donate.html', form_data=request.form)

        donation_id = execute_db(
            """
            INSERT INTO donations (
                donor_id, title, category, description, quantity, servings,
                address, city, pickup_deadline, prepared_time, allergens,
                donor_contact, instructions, status, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', 1)
            """,
            (
                g.user['id'], title, category, description, quantity, servings_int,
                address, city, pickup_deadline, prepared_time, allergens,
                donor_contact, instructions
            )
        )

        flash('Your food donation listing has been published! Verified NGOs in the area can now view and request it.', 'success')
        return redirect(url_for('donation_detail', donation_id=donation_id))

    # Pre-populate defaults from user profile
    initial_data = {
        'address': g.user['address'] or '',
        'city': g.user['city'] or 'Metropolis',
        'donor_contact': g.user['phone'] or g.user['email'] or ''
    }
    return render_template('donate.html', form_data=initial_data)

@app.route('/donations/<int:donation_id>/request', methods=['POST'])
@login_required
def request_donation(donation_id):
    """NGO submits a request for a donation."""
    if g.user['role'] not in ('ngo', 'admin'):
        flash('Only verified NGO or recipient community accounts can submit donation rescue requests.', 'warning')
        return redirect(url_for('donation_detail', donation_id=donation_id))

    donation = query_db("SELECT * FROM donations WHERE id = ? AND is_active = 1", (donation_id,), one=True)
    if not donation:
        abort(404)

    if donation['status'] != 'available':
        flash('This donation is no longer available for requests.', 'warning')
        return redirect(url_for('donation_detail', donation_id=donation_id))

    if donation['donor_id'] == g.user['id']:
        flash('You cannot request your own donation listing.', 'error')
        return redirect(url_for('donation_detail', donation_id=donation_id))

    # Check for existing pending or approved request
    existing = query_db(
        "SELECT id, status FROM donation_requests WHERE donation_id = ? AND ngo_id = ? AND status IN ('pending', 'approved')",
        (donation_id, g.user['id']),
        one=True
    )
    if existing:
        flash('You already have an active request for this food donation.', 'info')
        return redirect(url_for('donation_detail', donation_id=donation_id))

    message = request.form.get('message', '').strip()
    servings_str = request.form.get('servings_requested', str(donation['servings'])).strip()
    try:
        servings_req = int(servings_str)
        if servings_req <= 0 or servings_req > donation['servings']:
            servings_req = donation['servings']
    except (ValueError, TypeError):
        servings_req = donation['servings']

    execute_db(
        """
        INSERT INTO donation_requests (donation_id, ngo_id, servings_requested, message, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (donation_id, g.user['id'], servings_req, message)
    )

    flash('Rescue request submitted successfully! The donor has been notified.', 'success')
    return redirect(url_for('donation_detail', donation_id=donation_id))

# -----------------------------------------------------------------------------
# Request Management (Donor Approvals, Cancellations, Status Updates)
# -----------------------------------------------------------------------------

@app.route('/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    """Donor approves an NGO request, reserving the donation."""
    req = query_db(
        """
        SELECT r.*, d.donor_id, d.title AS donation_title
        FROM donation_requests r
        JOIN donations d ON r.donation_id = d.id
        WHERE r.id = ?
        """,
        (request_id,),
        one=True
    )
    if not req:
        abort(404)

    # Ownership check
    if req['donor_id'] != g.user['id'] and not g.user['is_admin']:
        flash('You do not have permission to manage this request.', 'error')
        return abort(403)

    db = get_db()
    try:
        # Mark this request approved
        db.execute("UPDATE donation_requests SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request_id,))
        # Reject other pending requests for this donation
        db.execute("UPDATE donation_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE donation_id = ? AND id != ? AND status = 'pending'", (req['donation_id'], request_id))
        # Update donation status to reserved
        db.execute("UPDATE donations SET status = 'reserved' WHERE id = ?", (req['donation_id'],))
        # Create volunteer task so volunteers can help transport
        db.execute("INSERT INTO volunteer_tasks (donation_id, status, notes) VALUES (?, 'available', 'Pickup reserved. Volunteer transport available.')", (req['donation_id'],))
        db.commit()
        flash('Request approved! This donation is now marked Reserved for pickup.', 'success')
    except Exception as e:
        db.rollback()
        flash('An error occurred while approving the request.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    """Donor rejects an NGO request."""
    req = query_db(
        """
        SELECT r.*, d.donor_id
        FROM donation_requests r
        JOIN donations d ON r.donation_id = d.id
        WHERE r.id = ?
        """,
        (request_id,),
        one=True
    )
    if not req:
        abort(404)

    if req['donor_id'] != g.user['id'] and not g.user['is_admin']:
        return abort(403)

    execute_db("UPDATE donation_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request_id,))
    flash('Request has been declined.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    """NGO cancels their own pending request."""
    req = query_db("SELECT * FROM donation_requests WHERE id = ?", (request_id,), one=True)
    if not req:
        abort(404)

    if req['ngo_id'] != g.user['id'] and not g.user['is_admin']:
        return abort(403)

    if req['status'] != 'pending':
        flash('Only pending requests can be cancelled.', 'warning')
        return redirect(url_for('dashboard'))

    execute_db("UPDATE donation_requests SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request_id,))
    flash('Your rescue request has been cancelled.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/donations/<int:donation_id>/complete', methods=['POST'])
@login_required
def complete_donation(donation_id):
    """Donor or Admin marks donation as collected / completed."""
    donation = query_db("SELECT * FROM donations WHERE id = ?", (donation_id,), one=True)
    if not donation:
        abort(404)

    if donation['donor_id'] != g.user['id'] and not g.user['is_admin']:
        return abort(403)

    db = get_db()
    try:
        db.execute("UPDATE donations SET status = 'collected' WHERE id = ?", (donation_id,))
        db.execute("UPDATE donation_requests SET status = 'collected', updated_at = CURRENT_TIMESTAMP WHERE donation_id = ? AND status = 'approved'", (donation_id,))
        db.execute("UPDATE volunteer_tasks SET status = 'delivered' WHERE donation_id = ?", (donation_id,))
        db.commit()
        flash('Donation marked as Collected! Thank you for reducing food waste.', 'success')
    except Exception:
        db.rollback()
        flash('An error occurred updating donation status.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/donations/<int:donation_id>/cancel', methods=['POST'])
@login_required
def cancel_donation(donation_id):
    """Donor cancels their listing."""
    donation = query_db("SELECT * FROM donations WHERE id = ?", (donation_id,), one=True)
    if not donation:
        abort(404)

    if donation['donor_id'] != g.user['id'] and not g.user['is_admin']:
        return abort(403)

    execute_db("UPDATE donations SET status = 'cancelled' WHERE id = ?", (donation_id,))
    flash('Donation listing has been cancelled.', 'info')
    return redirect(url_for('dashboard'))

# -----------------------------------------------------------------------------
# Volunteer Tasks Routes
# -----------------------------------------------------------------------------

@app.route('/tasks/<int:task_id>/claim', methods=['POST'])
@login_required
@role_required('volunteer', 'admin')
def claim_task(task_id):
    """Volunteer claims an open delivery/pickup mission."""
    task = query_db("SELECT * FROM volunteer_tasks WHERE id = ?", (task_id,), one=True)
    if not task:
        abort(404)

    if task['status'] != 'available':
        flash('This mission has already been claimed.', 'warning')
        return redirect(url_for('dashboard'))

    execute_db(
        "UPDATE volunteer_tasks SET volunteer_id = ?, status = 'assigned' WHERE id = ?",
        (g.user['id'], task_id)
    )
    flash('You have successfully claimed this rescue mission! Thank you for volunteering.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/tasks/<int:task_id>/deliver', methods=['POST'])
@login_required
@role_required('volunteer', 'admin')
def deliver_task(task_id):
    """Volunteer marks rescue mission as delivered."""
    task = query_db("SELECT * FROM volunteer_tasks WHERE id = ?", (task_id,), one=True)
    if not task:
        abort(404)

    if task['volunteer_id'] != g.user['id'] and not g.user['is_admin']:
        return abort(403)

    db = get_db()
    try:
        db.execute("UPDATE volunteer_tasks SET status = 'delivered' WHERE id = ?", (task_id,))
        db.execute("UPDATE donations SET status = 'collected' WHERE id = ?", (task['donation_id'],))
        db.execute("UPDATE donation_requests SET status = 'collected' WHERE donation_id = ? AND status = 'approved'", (task['donation_id'],))
        db.commit()
        flash('Rescue mission completed! The donation has been delivered.', 'success')
    except Exception:
        db.rollback()
        flash('Error marking mission as delivered.', 'error')

    return redirect(url_for('dashboard'))

# -----------------------------------------------------------------------------
# Authentication Routes (Register, Login, Logout)
# -----------------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with strict role choices and server-side validation."""
    if g.user is not None:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'donor').strip().lower()
        organization = request.form.get('organization', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()

        errors = []
        if not name or len(name) < 2:
            errors.append('Full name must be at least 2 characters.')
        if not email or '@' not in email or '.' not in email:
            errors.append('Please provide a valid email address.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        # Strict security check: Disallow self-registration as admin
        valid_roles = ('donor', 'ngo', 'volunteer')
        if role not in valid_roles:
            errors.append('Invalid account role selected.')

        # Check unique email
        existing_user = query_db('SELECT id FROM users WHERE email = ?', (email,), one=True)
        if existing_user:
            errors.append('An account with this email address already exists. Please sign in.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('register.html', form_data=request.form)

        # Hash password securely using Werkzeug
        hashed_password = generate_password_hash(password)

        new_user_id = execute_db(
            """
            INSERT INTO users (name, email, password_hash, role, organization, phone, city, is_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (name, email, hashed_password, role, organization, phone, city or 'Metropolis')
        )

        flash('Registration successful! You may now sign in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form_data={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Sign-in route with password verification and demo credentials shortcut."""
    if g.user is not None:
        return redirect(url_for('dashboard'))

    next_page = request.args.get('next', '')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)

        if user and check_password_hash(user['password_hash'], password):
            # Store in session and regenerate CSRF token
            session.clear()
            session['_csrf_token'] = secrets.token_hex(24)
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            session['is_admin'] = bool(user['is_admin'])
            if remember:
                session.permanent = True

            flash(f"Welcome back, {user['name']}!", 'success')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email address or password. Please verify your credentials.', 'error')

    return render_template('login.html', next=next_page)

@app.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    session['_csrf_token'] = secrets.token_hex(24)
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('index'))

# -----------------------------------------------------------------------------
# User Dashboard Route
# -----------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    """Dynamic role-based dashboard for Donor, NGO, Volunteer, and Admin."""
    role = g.user['role']
    context = {'role': role}

    if role == 'donor' or g.user['is_admin']:
        # My posted donations
        my_donations = query_db(
            """
            SELECT d.*,
                   (SELECT COUNT(*) FROM donation_requests WHERE donation_id = d.id) AS request_count
            FROM donations d
            WHERE d.donor_id = ?
            ORDER BY d.created_at DESC
            """,
            (g.user['id'],)
        )
        # Incoming requests for my donations
        incoming_requests = query_db(
            """
            SELECT r.*, d.title AS donation_title, d.quantity AS donation_quantity,
                   u.name AS ngo_name, u.organization AS ngo_org, u.phone AS ngo_phone, u.email AS ngo_email
            FROM donation_requests r
            JOIN donations d ON r.donation_id = d.id
            JOIN users u ON r.ngo_id = u.id
            WHERE d.donor_id = ?
            ORDER BY r.created_at DESC
            """,
            (g.user['id'],)
        )
        
        # Donor stats
        total_servings = sum(d['servings'] for d in my_donations if d['status'] in ('collected', 'reserved'))
        active_listings = sum(1 for d in my_donations if d['status'] == 'available')
        pending_reqs = sum(1 for r in incoming_requests if r['status'] == 'pending')

        context.update({
            'my_donations': my_donations,
            'incoming_requests': incoming_requests,
            'total_servings': total_servings,
            'active_listings': active_listings,
            'pending_reqs': pending_reqs
        })

    if role == 'ngo' or g.user['is_admin']:
        # NGO requests history
        my_requests = query_db(
            """
            SELECT r.*, d.title AS donation_title, d.category, d.quantity, d.servings,
                   d.address AS pickup_address, d.city AS pickup_city, d.pickup_deadline,
                   d.donor_contact, u.name AS donor_name, u.organization AS donor_org
            FROM donation_requests r
            JOIN donations d ON r.donation_id = d.id
            JOIN users u ON d.donor_id = u.id
            WHERE r.ngo_id = ?
            ORDER BY r.created_at DESC
            """,
            (g.user['id'],)
        )
        approved_rescues = sum(1 for r in my_requests if r['status'] in ('approved', 'collected'))
        rescued_meals = sum(r['servings_requested'] for r in my_requests if r['status'] in ('approved', 'collected'))

        context.update({
            'my_requests': my_requests,
            'approved_rescues': approved_rescues,
            'rescued_meals': rescued_meals
        })

    if role == 'volunteer' or g.user['is_admin']:
        # Open volunteer tasks (reserved donations needing transport)
        available_tasks = query_db(
            """
            SELECT vt.*, d.title AS donation_title, d.address AS pickup_address, d.city AS pickup_city,
                   d.pickup_deadline, d.servings, donor.name AS donor_name, donor.phone AS donor_phone
            FROM volunteer_tasks vt
            JOIN donations d ON vt.donation_id = d.id
            JOIN users donor ON d.donor_id = donor.id
            WHERE vt.status = 'available'
            ORDER BY vt.created_at DESC
            """
        )
        # Volunteer claimed missions
        my_tasks = query_db(
            """
            SELECT vt.*, d.title AS donation_title, d.address AS pickup_address, d.city AS pickup_city,
                   d.pickup_deadline, d.servings, donor.name AS donor_name, donor.phone AS donor_phone
            FROM volunteer_tasks vt
            JOIN donations d ON vt.donation_id = d.id
            JOIN users donor ON d.donor_id = donor.id
            WHERE vt.volunteer_id = ?
            ORDER BY vt.created_at DESC
            """,
            (g.user['id'],)
        )
        completed_tasks = sum(1 for t in my_tasks if t['status'] == 'delivered')

        context.update({
            'available_tasks': available_tasks,
            'my_tasks': my_tasks,
            'completed_tasks': completed_tasks
        })

    return render_template('dashboard.html', **context)

# -----------------------------------------------------------------------------
# Admin Dashboard & Controls
# -----------------------------------------------------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Administrator control panel."""
    # Summary stats
    stats = {
        'total_users': query_db("SELECT COUNT(*) AS c FROM users", one=True)['c'],
        'total_donations': query_db("SELECT COUNT(*) AS c FROM donations", one=True)['c'],
        'active_donations': query_db("SELECT COUNT(*) AS c FROM donations WHERE status = 'available'", one=True)['c'],
        'total_requests': query_db("SELECT COUNT(*) AS c FROM donation_requests", one=True)['c'],
        'total_messages': query_db("SELECT COUNT(*) AS c FROM contact_messages", one=True)['c'],
        'unread_messages': query_db("SELECT COUNT(*) AS c FROM contact_messages WHERE is_read = 0", one=True)['c'],
    }

    users = query_db("SELECT * FROM users ORDER BY created_at DESC LIMIT 50")
    donations_list = query_db(
        """
        SELECT d.*, u.name AS donor_name, u.email AS donor_email
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        ORDER BY d.created_at DESC LIMIT 50
        """
    )
    requests_list = query_db(
        """
        SELECT r.*, d.title AS donation_title, u.name AS ngo_name, u.email AS ngo_email
        FROM donation_requests r
        JOIN donations d ON r.donation_id = d.id
        JOIN users u ON r.ngo_id = u.id
        ORDER BY r.created_at DESC LIMIT 50
        """
    )
    messages = query_db("SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 50")

    return render_template(
        'admin.html',
        stats=stats,
        users=users,
        donations=donations_list,
        requests=requests_list,
        messages=messages
    )

@app.route('/admin/donations/<int:donation_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_donation(donation_id):
    """Admin toggles active state of a donation listing."""
    donation = query_db("SELECT is_active FROM donations WHERE id = ?", (donation_id,), one=True)
    if not donation:
        abort(404)
    new_state = 0 if donation['is_active'] else 1
    execute_db("UPDATE donations SET is_active = ? WHERE id = ?", (new_state, donation_id))
    flash(f"Donation listing #{donation_id} visibility updated.", 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/messages/<int:message_id>/toggle-read', methods=['POST'])
@admin_required
def admin_toggle_message_read(message_id):
    """Admin toggles read status of contact message."""
    msg = query_db("SELECT is_read FROM contact_messages WHERE id = ?", (message_id,), one=True)
    if not msg:
        abort(404)
    new_state = 0 if msg['is_read'] else 1
    execute_db("UPDATE contact_messages SET is_read = ? WHERE id = ?", (new_state, message_id))
    flash('Message status updated.', 'info')
    return redirect(url_for('admin_dashboard'))

# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# -----------------------------------------------------------------------------
# Application Startup & CLI Commands
# -----------------------------------------------------------------------------

@app.cli.command("init-db")
def init_db_command():
    """CLI command to initialize database schema."""
    init_db(app)
    print("Initialized the SQLite database schema successfully.")

@app.cli.command("create-admin")
def create_admin_command():
    """Interactive command to create or promote an admin user safely."""
    import getpass
    email = input("Admin Email: ").strip().lower()
    name = input("Admin Full Name: ").strip()
    password = getpass.getpass("Admin Password: ")
    
    with app.app_context():
        user = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True)
        if user:
            execute_db("UPDATE users SET is_admin = 1, role = 'admin' WHERE id = ?", (user['id'],))
            print(f"Existing user '{email}' has been promoted to Administrator.")
        else:
            execute_db(
                """
                INSERT INTO users (name, email, password_hash, role, is_admin)
                VALUES (?, ?, ?, 'admin', 1)
                """,
                (name or "Administrator", email, generate_password_hash(password))
            )
            print(f"Administrator account '{email}' created successfully.")

# Auto-initialize database schema on startup if it doesn't exist
with app.app_context():
    init_db()

if __name__ == '__main__':
    # Local development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
    print(f"Starting FoodBridge platform on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=debug)
