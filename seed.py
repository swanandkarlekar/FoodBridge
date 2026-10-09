"""
FoodBridge Database Seeder
Populates realistic demonstration accounts, food donations, requests, and inquiries.
Safe to run multiple times: checks existing records before insertion.
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app
from db import query_db, execute_db

def seed_database():
    with app.app_context():
        print("Starting FoodBridge database seeding...")

        # 1. Seed Users (Donors, NGOs, Volunteers, Admin)
        users_to_seed = [
            {
                "email": "donor@foodbridge.org",
                "name": "Marcus Vance",
                "password": "FoodBridge123!",
                "role": "donor",
                "organization": "GreenLeaf Bistro & Catering",
                "phone": "+1 (555) 234-5678",
                "address": "452 Elm Street, Downtown",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "bakery@foodbridge.org",
                "name": "Elena Rostova",
                "password": "FoodBridge123!",
                "role": "donor",
                "organization": "Artisan Hearth Bakery",
                "phone": "+1 (555) 345-6789",
                "address": "128 Baker Avenue",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "hotel@foodbridge.org",
                "name": "David Chen",
                "password": "FoodBridge123!",
                "role": "donor",
                "organization": "Grand Plaza Hotel & Banquets",
                "phone": "+1 (555) 456-7890",
                "address": "800 Harbor Boulevard",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "ngo@foodbridge.org",
                "name": "Sarah Jenkins",
                "password": "FoodBridge123!",
                "role": "ngo",
                "organization": "Hope Community Kitchen & Shelter",
                "phone": "+1 (555) 876-5432",
                "address": "304 Mission Way",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "table@foodbridge.org",
                "name": "Carlos Mendoza",
                "password": "FoodBridge123!",
                "role": "ngo",
                "organization": "City Harvest Relief Coalition",
                "phone": "+1 (555) 987-6543",
                "address": "710 Community Drive",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "volunteer@foodbridge.org",
                "name": "Alex Rivera",
                "password": "FoodBridge123!",
                "role": "volunteer",
                "organization": "Green Fleet Couriers",
                "phone": "+1 (555) 312-7890",
                "address": "52 Bicycle Lane",
                "city": "Metropolis",
                "is_admin": 0
            },
            {
                "email": "admin@foodbridge.org",
                "name": "Platform Administrator",
                "password": "AdminSecret2026!",
                "role": "admin",
                "organization": "FoodBridge Operations",
                "phone": "+1 (555) 100-2000",
                "address": "100 Innovation Plaza",
                "city": "Metropolis",
                "is_admin": 1
            }
        ]

        user_map = {}
        for u in users_to_seed:
            existing = query_db("SELECT id, role, is_admin FROM users WHERE email = ?", (u['email'],), one=True)
            if existing:
                user_map[u['email']] = existing['id']
                print(f"  User '{u['email']}' already exists (ID: {existing['id']}).")
            else:
                uid = execute_db(
                    """
                    INSERT INTO users (name, email, password_hash, role, organization, phone, address, city, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        u['name'], u['email'], generate_password_hash(u['password']),
                        u['role'], u['organization'], u['phone'], u['address'],
                        u['city'], u['is_admin']
                    )
                )
                user_map[u['email']] = uid
                print(f"  Created user: {u['name']} <{u['email']}> [{u['role']}]")

        # 2. Seed Food Donations
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d 18:00")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d 20:00")
        three_days = (now + timedelta(days=3)).strftime("%Y-%m-%d 14:00")
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d 17:00")
        past_week = (now - timedelta(days=4)).strftime("%Y-%m-%d 12:00")

        donations_to_seed = [
            {
                "donor_email": "bakery@foodbridge.org",
                "title": "Fresh Artisan Sourdough Loaves & Croissants",
                "category": "Bakery",
                "description": "Daily surplus of naturally leavened sourdough bread and buttery croissants from this morning's bake. Packaged in sanitized food-grade paper bags.",
                "quantity": "35 sourdough loaves & 50 croissants",
                "servings": 85,
                "address": "128 Baker Avenue",
                "city": "Metropolis",
                "pickup_deadline": tomorrow,
                "prepared_time": "Today, 6:00 AM",
                "allergens": "Contains Gluten, Wheat, Milk/Dairy (croissants)",
                "donor_contact": "+1 (555) 345-6789",
                "instructions": "Come to the rear alley entrance next to loading bay 2. Knock and ask for Elena.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "donor@foodbridge.org",
                "title": "Mediterranean Catering Buffet Trays (Chicken, Falafel & Rice)",
                "category": "Cooked Meals",
                "description": "High quality untouched banquet surplus: Seasoned roasted chicken breasts, crispy herb falafel, spiced turmeric basmati rice, and grilled seasonal vegetables. Kept in temperature-controlled cambro warmers.",
                "quantity": "8 hotel pans (full size)",
                "servings": 75,
                "address": "452 Elm Street, Downtown",
                "city": "Metropolis",
                "pickup_deadline": tomorrow,
                "prepared_time": "Today, 2:30 PM",
                "allergens": "Chicken (Poultry), Sesame (Tahini sauce separately packed), Gluten-free options available",
                "donor_contact": "+1 (555) 234-5678",
                "instructions": "Front desk reception will direct you to the catering staging area.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "hotel@foodbridge.org",
                "title": "Organic Farm Crisp Apples & Mixed Bell Peppers",
                "category": "Fresh Produce",
                "description": "Surplus delivery of Grade-A organic Fuji apples, sweet red bell peppers, and romaine lettuce hearts directly from regional cooperative growers.",
                "quantity": "4 wooden crates (~45 kg)",
                "servings": 110,
                "address": "800 Harbor Boulevard",
                "city": "Metropolis",
                "pickup_deadline": day_after,
                "prepared_time": "Farm harvested 24h ago",
                "allergens": "None (Raw fresh produce)",
                "donor_contact": "+1 (555) 456-7890",
                "instructions": "Loading dock on Harbor Lane. Ring the goods receiving bell.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "donor@foodbridge.org",
                "title": "Slow-Simmered Vegetable Minestrone & Focaccia Bread",
                "category": "Cooked Meals",
                "description": "Rich vegetable soup prepared with heirloom tomatoes, kidney beans, zucchini, and pasta shells, served with rosemary focaccia squares.",
                "quantity": "3 insulated food drums (approx 40 liters)",
                "servings": 60,
                "address": "452 Elm Street, Downtown",
                "city": "Metropolis",
                "pickup_deadline": three_days,
                "prepared_time": "Today, 11:00 AM",
                "allergens": "Vegetarian, Vegan-friendly, Contains Gluten (in pasta/focaccia)",
                "donor_contact": "+1 (555) 234-5678",
                "instructions": "Bring soup transport vessels or swap with sanitized commercial stock pots.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "hotel@foodbridge.org",
                "title": "Cold-Chain Dairy & Barista Oat Milk Cartons",
                "category": "Dairy",
                "description": "Chilled pasteurized whole milk cartons and certified gluten-free oat milk cartons. Well within best-by dates (5 days remaining). Stored in walk-in cold room at 3°C.",
                "quantity": "28 half-gallon cartons",
                "servings": 55,
                "address": "800 Harbor Boulevard",
                "city": "Metropolis",
                "pickup_deadline": day_after,
                "prepared_time": "Refrigerated storage",
                "allergens": "Contains Dairy / Cow Milk; Oat milk is nut-free and dairy-free",
                "donor_contact": "+1 (555) 456-7890",
                "instructions": "Please bring thermal cooler bags or refrigerated vehicle.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "donor@foodbridge.org",
                "title": "Individual Granola & Dried Fruit Energy Packs",
                "category": "Packaged Goods",
                "description": "Commercial factory-sealed packages of mixed berry granola bars, roasted almonds, and unsweetened dried fruit packs. Great for distribution kits.",
                "quantity": "140 individually sealed units",
                "servings": 140,
                "address": "452 Elm Street, Downtown",
                "city": "Metropolis",
                "pickup_deadline": three_days,
                "prepared_time": "Factory shelf-stable",
                "allergens": "Contains Almonds and Oats. May contain soy traces.",
                "donor_contact": "+1 (555) 234-5678",
                "instructions": "Available for pickup anytime during business hours 9am-6pm.",
                "status": "available",
                "is_active": 1
            },
            {
                "donor_email": "donor@foodbridge.org",
                "title": "Baked Eggplant & Ricotta Lasagna Trays",
                "category": "Cooked Meals",
                "description": "Surplus from an executive luncheon. Vegetarian lasagna made with layered pasta, roasted eggplant, marinara sauce, and ricotta/mozzarella cheese.",
                "quantity": "5 full trays",
                "servings": 40,
                "address": "452 Elm Street, Downtown",
                "city": "Metropolis",
                "pickup_deadline": tomorrow,
                "prepared_time": "Yesterday, 3:00 PM",
                "allergens": "Contains Gluten, Dairy, Eggs (Vegetarian)",
                "donor_contact": "+1 (555) 234-5678",
                "instructions": "Refrigerated and ready for pickup.",
                "status": "reserved",
                "is_active": 1
            },
            {
                "donor_email": "bakery@foodbridge.org",
                "title": "Breakfast Bagels & Artisan Cream Cheese Spreads",
                "category": "Bakery",
                "description": "Fresh assorted sesame, plain, and whole wheat bagels from weekend brunch service.",
                "quantity": "45 assorted bagels",
                "servings": 45,
                "address": "128 Baker Avenue",
                "city": "Metropolis",
                "pickup_deadline": past_week,
                "prepared_time": "Past weekend",
                "allergens": "Contains Gluten, Sesame, Dairy",
                "donor_contact": "+1 (555) 345-6789",
                "instructions": "Already collected by community partner.",
                "status": "collected",
                "is_active": 1
            }
        ]

        donation_map = {}
        for d in donations_to_seed:
            donor_id = user_map.get(d['donor_email'])
            if not donor_id:
                continue

            existing = query_db(
                "SELECT id FROM donations WHERE title = ? AND donor_id = ?",
                (d['title'], donor_id),
                one=True
            )
            if existing:
                donation_map[d['title']] = existing['id']
                print(f"  Donation '{d['title'][:35]}...' already exists (ID: {existing['id']}).")
            else:
                did = execute_db(
                    """
                    INSERT INTO donations (
                        donor_id, title, category, description, quantity, servings,
                        address, city, pickup_deadline, prepared_time, allergens,
                        donor_contact, instructions, status, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        donor_id, d['title'], d['category'], d['description'],
                        d['quantity'], d['servings'], d['address'], d['city'],
                        d['pickup_deadline'], d['prepared_time'], d['allergens'],
                        d['donor_contact'], d['instructions'], d['status'], d['is_active']
                    )
                )
                donation_map[d['title']] = did
                print(f"  Created donation: '{d['title'][:40]}' (ID: {did})")

        # 3. Seed Requests for Reserved / Collected items
        ngo_hope_id = user_map.get("ngo@foodbridge.org")
        ngo_harvest_id = user_map.get("table@foodbridge.org")
        volunteer_alex_id = user_map.get("volunteer@foodbridge.org")

        # Request for Reserved item (Lasagna)
        lasagna_id = donation_map.get("Baked Eggplant & Ricotta Lasagna Trays")
        if lasagna_id and ngo_hope_id:
            existing_req = query_db("SELECT id FROM donation_requests WHERE donation_id = ? AND ngo_id = ?", (lasagna_id, ngo_hope_id), one=True)
            if not existing_req:
                execute_db(
                    """
                    INSERT INTO donation_requests (donation_id, ngo_id, servings_requested, message, status)
                    VALUES (?, ?, 40, 'Hope Shelter evening meal service. We have refrigerated van pickup ready.', 'approved')
                    """,
                    (lasagna_id, ngo_hope_id)
                )
                # Seed volunteer task
                execute_db(
                    """
                    INSERT INTO volunteer_tasks (donation_id, volunteer_id, status, notes)
                    VALUES (?, ?, 'assigned', 'Volunteer Alex Rivera assigned to assist with transport to Hope Shelter.')
                    """,
                    (lasagna_id, volunteer_alex_id)
                )
                print("  Created approved request and volunteer task for Reserved Lasagna.")

        # Request for Collected item (Bagels)
        bagels_id = donation_map.get("Breakfast Bagels & Artisan Cream Cheese Spreads")
        if bagels_id and ngo_hope_id:
            existing_req = query_db("SELECT id FROM donation_requests WHERE donation_id = ? AND ngo_id = ?", (bagels_id, ngo_hope_id), one=True)
            if not existing_req:
                execute_db(
                    """
                    INSERT INTO donation_requests (donation_id, ngo_id, servings_requested, message, status)
                    VALUES (?, ?, 45, 'Collected for Sunday community breakfast program.', 'collected')
                    """,
                    (bagels_id, ngo_hope_id)
                )
                print("  Created collected request record for Bagels.")

        # Pending Request for Mediterranean Buffet
        med_id = donation_map.get("Mediterranean Catering Buffet Trays (Chicken, Falafel & Rice)")
        if med_id and ngo_harvest_id:
            existing_req = query_db("SELECT id FROM donation_requests WHERE donation_id = ? AND ngo_id = ?", (med_id, ngo_harvest_id), one=True)
            if not existing_req:
                execute_db(
                    """
                    INSERT INTO donation_requests (donation_id, ngo_id, servings_requested, message, status)
                    VALUES (?, ?, 60, 'Our mobile food distribution van can pick this up tomorrow at 3 PM. Thank you!', 'pending')
                    """,
                    (med_id, ngo_harvest_id)
                )
                print("  Created pending request for Mediterranean Catering.")

        # 4. Seed Sample Contact Messages
        sample_messages = [
            (
                "Riverside Convention Center",
                "events@riversidecenter.com",
                "Banquet Food Rescue Partnership",
                "Partnership",
                "We host weekly multi-course conferences with 200-500 guests and would like to set up an ongoing automated surplus collection partnership with FoodBridge.",
                0
            ),
            (
                "Maria Santos",
                "maria.s@communityvoice.org",
                "Volunteer Training Guidelines",
                "Volunteer Inquiry",
                "Our youth group wants to join the weekend bicycle courier rescue squad. Do you hold orientation sessions for safe food handling?",
                1
            )
        ]

        for name, email, subject, category, message, is_read in sample_messages:
            existing_msg = query_db("SELECT id FROM contact_messages WHERE email = ? AND subject = ?", (email, subject), one=True)
            if not existing_msg:
                execute_db(
                    """
                    INSERT INTO contact_messages (name, email, subject, category, message, is_read)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, email, subject, category, message, is_read)
                )
                print(f"  Created contact message from: {name}")

        print("\nSeed completed successfully!")
        print("----------------------------------------------------------------")
        print("Demo Accounts:")
        print("  1. Food Donor:      donor@foodbridge.org       / FoodBridge123!")
        print("  2. Bakery Donor:    bakery@foodbridge.org      / FoodBridge123!")
        print("  3. Verified NGO:    ngo@foodbridge.org         / FoodBridge123!")
        print("  4. Community NGO:   table@foodbridge.org       / FoodBridge123!")
        print("  5. Volunteer Hero:  volunteer@foodbridge.org   / FoodBridge123!")
        print("  6. Administrator:   admin@foodbridge.org       / AdminSecret2026!")
        print("----------------------------------------------------------------")

if __name__ == '__main__':
    seed_database()
