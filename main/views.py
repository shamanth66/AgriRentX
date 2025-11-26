from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from .models import CustomUser, AgricultureItem, RentalRequest, StockNotification
from .forms import SignupForm, OTPVerifyForm, AgricultureItemForm, OTPRequestForm
import random

# Add these new imports at the top
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from decimal import Decimal, InvalidOperation

# Import the new Aadhaar form
from .forms import AadhaarVerificationForm

# ------------------ ADMIN CREDENTIALS ------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ------------------ HELPER ------------------
def generate_otp():
    """Generate a 7-digit numeric OTP"""
    return str(random.randint(1000000, 9999999))


# ------------------ LANDING / INFO PAGES ------------------
def landing_page(request):
    return render(request, 'landing.html')

def about_page(request):
    return render(request, 'about.html')

def contact_page(request):
    return render(request, 'contact.html')


# ------------------ LOGOUT ------------------
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('landing')


# ------------------ SIGNUP ------------------
# ------------------ SIGNUP ------------------
def user_signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.role = 'user'
                user.status = 'approved'  # Auto-approve for testing
                user.save()
                
                # Debug print
                print(f"User created: {user.username}, {user.email}")
                print(f"User ID: {user.id}")
                
                messages.success(request, "Signup successful! Please sign in via OTP.")
                return redirect('user_signin')
                
            except Exception as e:
                print(f"Error creating user: {str(e)}")
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            # Print form errors for debugging
            print("Form errors:", form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupForm()
    
    return render(request, 'user_signup.html', {'form': form})


# ------------------ SIGNIN (Request OTP) ------------------
def user_signin(request):
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(username=username, email=email, role='user')
                otp = generate_otp()
                request.session['user_otp'] = otp
                request.session['user_id'] = user.id
                # Send OTP via email
                send_mail(
                    subject='Your Agri-RentX OTP',
                    message=f'Hello {user.username}, your OTP is: {otp}',
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "OTP sent to your email!")
                return redirect('user_verify_otp')
            except CustomUser.DoesNotExist:
                messages.error(request, "Invalid username or email.")
    else:
        form = OTPRequestForm()
    return render(request, 'user_request_otp.html', {'form': form})


def admin_signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check predefined admin credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            try:
                # Get or create admin user
                admin, created = CustomUser.objects.get_or_create(
                    username=ADMIN_USERNAME,
                    defaults={
                        'email': 'admin@agrirentx.com',
                        'role': 'admin',
                        'status': 'approved',
                        'is_aadhaar_verified': True
                    }
                )
                
                # Set a default password for the admin user
                if created:
                    admin.set_password('admin123')
                    admin.save()
                
                # Log in the admin
                login(request, admin, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, "Admin login successful!")
                return redirect('admin_dashboard')
                
            except Exception as e:
                messages.error(request, f"Login error: {str(e)}")
        else:
            messages.error(request, "Invalid admin credentials")
    
    return render(request, 'admin_login.html')


# ------------------ OTP VERIFY ------------------
def user_verify_otp(request):
    # Check if OTP was actually requested (session exists)
    if 'user_otp' not in request.session or 'user_id' not in request.session:
        messages.error(request, "Please request an OTP first")
        return redirect('user_signin')
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            session_otp = request.session.get('user_otp')
            user_id = request.session.get('user_id')
            
            if otp == session_otp:
                try:
                    user = CustomUser.objects.get(id=user_id, role='user')
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    # Clean up session
                    if 'user_otp' in request.session:
                        del request.session['user_otp']
                    if 'user_id' in request.session:
                        del request.session['user_id']
                    request.session.save()
                    
                    messages.success(request, "Login successful!")
                    return redirect('user_dashboard')
                except CustomUser.DoesNotExist:
                    messages.error(request, "User not found")
                    return redirect('user_signin')
            else:
                messages.error(request, "Invalid OTP")
    else:
        form = OTPVerifyForm()
    
    return render(request, 'user_verify_otp.html', {'form': form})


# ------------------ AADHAAR VERIFICATION (NEW) ------------------
@login_required
def aadhaar_verification(request):
    """Aadhaar verification page for users"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # Check if already verified
    if request.user.is_aadhaar_verified:
        messages.info(request, "Your Aadhaar is already verified!")
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = AadhaarVerificationForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_aadhaar_verified = False  # Admin needs to verify
            user.save()
            messages.success(request, "Aadhaar documents uploaded successfully! Waiting for admin verification.")
            return redirect('user_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AadhaarVerificationForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'aadhaar_verification.html', context)


# ------------------ DASHBOARDS ------------------
@login_required
def user_dashboard(request):
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')

    # Import here to avoid circular imports
    from .models import RentalRequest, AgricultureItem

    # Get all items (available and unavailable)
    items = AgricultureItem.objects.all()
    rentals = RentalRequest.objects.filter(user=request.user)
    
    # Calculate active rentals count (approved and not returned)
    active_rentals_count = rentals.filter(status='approved', is_returned=False).count()

    # NEW: Get new items (added in the last 7 days)
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    new_items = AgricultureItem.objects.filter(
        created_at__gte=seven_days_ago,
        is_available=True
    ).order_by('-created_at')
    
    # Count new items for notification badge
    new_items_count = new_items.count()
    
    # NEW: Get user's last login to show items added since then
    user_last_login = request.user.last_login
    if user_last_login:
        items_since_last_login = AgricultureItem.objects.filter(
            created_at__gte=user_last_login,
            is_available=True
        ).count()
    else:
        items_since_last_login = new_items_count

    # NEW: Get deadline notifications for active rentals
    deadline_notifications = []
    active_rentals = rentals.filter(status='approved', is_returned=False)
    
    for rental in active_rentals:
        days_left = rental.days_until_deadline()
        if days_left is not None and days_left <= 3:  # Notify if 3 days or less
            deadline_notifications.append({
                'rental': rental,
                'days_left': days_left,
                'message': f"Return deadline for {rental.item.name} in {days_left} day(s)"
            })

    # NEW: Check for back-in-stock notifications
    back_in_stock_notifications = StockNotification.objects.filter(
        user=request.user,
        item__is_available=True,
        notified=True
    )

    context = {
        'items': items,
        'rentals': rentals,
        'active_rentals_count': active_rentals_count,
        'new_items': new_items,
        'new_items_count': new_items_count,
        'items_since_last_login': items_since_last_login,
        'now': timezone.now(),
        'deadline_notifications': deadline_notifications,  # NEW
        'back_in_stock_notifications': back_in_stock_notifications,  # NEW
    }
    return render(request, 'user_dashboard.html', context)


@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')

    # Import here to avoid circular imports
    from .models import RentalRequest, AgricultureItem

    users = CustomUser.objects.filter(role='user')
    items = AgricultureItem.objects.all()
    rental_requests = RentalRequest.objects.all()
    
    # NEW: Get Aadhaar verification requests
    pending_verifications = CustomUser.objects.filter(
        role='user', 
        is_aadhaar_verified=False
    ).exclude(aadhaar_number__isnull=True).exclude(aadhaar_number='')
    
    verified_users = CustomUser.objects.filter(role='user', is_aadhaar_verified=True)

    # NEW: Get stock alerts
    out_of_stock_items = AgricultureItem.objects.filter(is_available=False)
    
    # NEW: Get pending back-in-stock notifications count
    pending_notifications_count = StockNotification.objects.filter(notified=False).count()

    # Handle adding new items
    if request.method == 'POST' and 'add_item' in request.POST:
        form = AgricultureItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.added_by = request.user
            item.is_available = True
            
            # NEW: Mark as new and set expiration
            item.is_new = True
            item.new_until = timezone.now() + timezone.timedelta(days=7)
            
            item.save()
            messages.success(request, "Item added successfully! Users will be notified about this new item.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, form.errors)
    else:
        form = AgricultureItemForm()

    context = {
        'users': users,
        'items': items,
        'rental_requests': rental_requests,
        'pending_verifications': pending_verifications,
        'verified_users': verified_users,
        'form': form,
        'now': timezone.now(),
        'out_of_stock_items': out_of_stock_items,  # NEW
        'pending_notifications_count': pending_notifications_count,  # NEW
    }
    return render(request, 'admin_dashboard.html', context)


# ------------------ RENTAL PROCESS ------------------
@login_required
def rental_terms(request, item_id):
    """Display rental terms and conditions for a specific item"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # UPDATED: Check Aadhaar verification - now required before accessing rental terms
    if not request.user.is_aadhaar_verified:
        messages.warning(request, "Please complete Aadhaar verification before viewing rental terms.")
        return redirect('aadhaar_verification')
    
    item = get_object_or_404(AgricultureItem, id=item_id)
    
    # NEW: Check if item is available
    if not item.is_available:
        messages.warning(request, f"Sorry, {item.name} is currently out of stock.")
        return redirect('user_dashboard')
    
    # Check if user already has a pending/approved request for this item
    existing_request = RentalRequest.objects.filter(
        user=request.user, 
        item=item, 
        status__in=['pending', 'approved']
    ).first()
    
    if existing_request:
        messages.info(request, f"You already have a {existing_request.status} request for {item.name}.")
        return redirect('user_dashboard')
    
    context = {
        'item': item,
    }
    return render(request, 'rental_terms.html', context)


@login_required
def accept_terms(request, item_id):
    """Handle terms acceptance and create rental request"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # UPDATED: Check Aadhaar verification - now required before accepting terms
    if not request.user.is_aadhaar_verified:
        messages.warning(request, "Please complete Aadhaar verification before renting items.")
        return redirect('aadhaar_verification')
    
    if request.method != 'POST':
        return redirect('rental_terms', item_id=item_id)
    
    item = get_object_or_404(AgricultureItem, id=item_id)
    
    # NEW: Check if item is available
    if not item.is_available:
        messages.warning(request, f"Sorry, {item.name} is no longer available.")
        return redirect('user_dashboard')
    
    # Check for existing request
    existing_request = RentalRequest.objects.filter(
        user=request.user, 
        item=item, 
        status__in=['pending', 'approved']
    ).first()
    
    if existing_request:
        messages.info(request, "You already have a request for this item.")
        return redirect('user_dashboard')
    
    # Create rental request with terms accepted
    rental = RentalRequest.objects.create(
        user=request.user,
        item=item,
        status='pending',
        terms_accepted=True
    )
    
    # Make item unavailable when rented
    item.is_available = False
    item.save()
    
    messages.success(request, "Terms accepted! Please proceed with advance payment.")
    return redirect('rental_payment', rental_id=rental.id)


@login_required
def rental_payment(request, rental_id):
    """Display payment page for rental request"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # UPDATED: Check Aadhaar verification - now required before payment
    if not request.user.is_aadhaar_verified:
        messages.warning(request, "Please complete Aadhaar verification before making payments.")
        return redirect('aadhaar_verification')
    
    rental = get_object_or_404(RentalRequest, id=rental_id, user=request.user)
    
    if not rental.terms_accepted:
        messages.error(request, "Please accept terms first.")
        return redirect('rental_terms', item_id=rental.item.id)
    
    if rental.advance_paid:
        messages.info(request, "Payment already completed for this rental.")
        return redirect('user_dashboard')
    
    # Calculate advance payment (50% of daily rate)
    advance_amount = rental.item.price_per_day * Decimal('0.5')
    
    context = {
        'rental': rental,
        'item': rental.item,
        'advance_amount': advance_amount,
        'phonepe_vpa': '8073220735@ybl',  # Replace with your PhonePe VPA
    }
    return render(request, 'rental_payment.html', context)


@login_required
def process_payment(request, rental_id):
    """Process the payment confirmation"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # UPDATED: Check Aadhaar verification - now required before processing payment
    if not request.user.is_aadhaar_verified:
        messages.warning(request, "Please complete Aadhaar verification before processing payments.")
        return redirect('aadhaar_verification')
    
    rental = get_object_or_404(RentalRequest, id=rental_id, user=request.user)

    if request.method == "POST":
        payment_method = request.POST.get('payment_method')

        if payment_method != "phonepe":
            messages.error(request, "Invalid payment method.")
            return redirect('rental_payment', rental_id=rental_id)

        # Mark advance as paid
        rental.advance_paid = True
        rental.save()

        messages.success(request, "Payment successful! Redirecting to dashboard.")
        return redirect('user_dashboard')

    return redirect('rental_payment', rental_id=rental_id)


# ------------------ STOCK NOTIFICATION VIEWS ------------------
@login_required
def notify_when_available(request, item_id):
    """User requests notification when item is back in stock"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    item = get_object_or_404(AgricultureItem, id=item_id)
    
    # Check if notification already exists
    notification, created = StockNotification.objects.get_or_create(
        user=request.user,
        item=item,
        defaults={'notified': False}
    )
    
    if created:
        messages.success(request, f"You'll be notified when {item.name} is back in stock!")
    else:
        messages.info(request, f"You're already subscribed to notifications for {item.name}")
    
    return redirect('user_dashboard')

@login_required
def remove_stock_notification(request, notification_id):
    """Remove back-in-stock notification"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    notification = get_object_or_404(StockNotification, id=notification_id, user=request.user)
    item_name = notification.item.name
    notification.delete()
    
    messages.success(request, f"Notification for {item_name} removed.")
    return redirect('user_dashboard')


# ------------------ ADMIN ACTIONS ------------------
@login_required
def change_user_status(request, user_id, status):
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')

    user = get_object_or_404(CustomUser, id=user_id, role='user')
    user.status = status
    user.save()
    messages.success(request, f"User '{user.username}' status updated to {status}.")
    return redirect('admin_dashboard')


@login_required
def change_item_availability(request, item_id):
    """Change item availability status"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')

    item = get_object_or_404(AgricultureItem, id=item_id)
    item.is_available = not item.is_available
    item.save()
    
    status = "available" if item.is_available else "unavailable"
    messages.success(request, f"Item '{item.name}' is now {status}.")
    return redirect('admin_dashboard')


@login_required
def change_rental_status(request, rental_id, status):
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')

    rental = get_object_or_404(RentalRequest, id=rental_id)

    # Check if terms & advance payment are completed before approving
    if status == 'approved' and not (rental.terms_accepted and rental.advance_paid):
        messages.warning(request, f"Cannot approve: '{rental.user.username}' has not accepted terms or made advance payment.")
        return redirect('admin_dashboard')

    rental.status = status
    rental.save()
    messages.success(request, f"Rental request for '{rental.item.name}' by '{rental.user.username}' updated to {status}.")
    return redirect('admin_dashboard')


@login_required
def update_rental_damage(request, rental_id):
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')

    rental = get_object_or_404(RentalRequest, id=rental_id)
    from .forms import RentalManagementForm
    form = RentalManagementForm(request.POST or None, instance=rental)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Rental '{rental.item.name}' updated with damage/penalty info.")
        return redirect('admin_dashboard')

    return render(request, 'update_rental_damage.html', {'form': form, 'rental': rental})


# ------------------ AADHAAR ADMIN ACTIONS (NEW) ------------------
@login_required
def verify_aadhaar(request, user_id):
    """Admin verify user Aadhaar"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    user = get_object_or_404(CustomUser, id=user_id, role='user')
    
    user.is_aadhaar_verified = True
    user.aadhaar_verification_date = timezone.now()
    user.save()
    
    messages.success(request, f"Aadhaar verified for {user.username}")
    return redirect('admin_dashboard')


@login_required
def reject_aadhaar(request, user_id):
    """Admin reject user Aadhaar"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    user = get_object_or_404(CustomUser, id=user_id, role='user')
    
    # Delete the uploaded files
    if user.aadhaar_front:
        user.aadhaar_front.delete()
    if user.aadhaar_back:
        user.aadhaar_back.delete()
    
    user.aadhaar_number = ''
    user.is_aadhaar_verified = False
    user.aadhaar_verification_date = None
    user.save()
    
    messages.warning(request, f"Aadhaar rejected for {user.username}. User needs to re-upload.")
    return redirect('admin_dashboard')


# ------------------ INVOICE GENERATION ------------------
@login_required
def generate_invoice_pdf(request, rental_id):
    """Generate PDF invoice for a rental"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    rental = get_object_or_404(RentalRequest, id=rental_id)
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#146eb4')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#232f3e')
    )
    
    normal_style = styles["Normal"]
    
    # Invoice Header
    elements.append(Paragraph("AGRI-RENTX INVOICE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Company and Invoice Details
    invoice_data = [
        ["Agri-RentX", f"Invoice #: INV-{rental.id:04d}"],
        ["Agriculture Equipment Rental", f"Date: {timezone.now().strftime('%Y-%m-%d')}"],
        ["admin@agrirentx.com", f"Due Date: {(timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')}"],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[3*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fafafa')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#232f3e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(invoice_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Billing Information
    elements.append(Paragraph("BILL TO:", heading_style))
    customer_info = [
        f"Name: {rental.user.username}",
        f"Email: {rental.user.email}",
        f"Phone: {rental.user.phone}",
        f"Address: {rental.user.address}"
    ]
    
    for info in customer_info:
        elements.append(Paragraph(info, normal_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Rental Details
    elements.append(Paragraph("RENTAL DETAILS:", heading_style))
    
    # Calculate amounts using Decimal
    advance_amount = (rental.item.price_per_day * Decimal('0.5')).quantize(Decimal('0.01'))
    penalty_amount = rental.penalty_amount if rental.penalty_amount else Decimal('0')
    total_amount = advance_amount + penalty_amount
    
    rental_data = [
        ["Description", "Amount"],
        [f"Equipment: {rental.item.name}", ""],
        [f"Category: {rental.item.category}", ""],
        [f"Daily Rate: ₹{rental.item.price_per_day}", ""],
        ["Advance Payment (50%)", f"₹{advance_amount:.2f}"],
    ]
    
    # Add penalty if applicable
    if penalty_amount > 0:
        rental_data.append(["Penalty Charge", f"₹{penalty_amount:.2f}"])
    
    rental_data.append(["TOTAL AMOUNT", f"₹{total_amount:.2f}"])
    
    rental_table = Table(rental_data, colWidths=[4*inch, 2*inch])
    rental_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#146eb4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(rental_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms and Conditions
    elements.append(Paragraph("TERMS & CONDITIONS:", heading_style))
    terms = [
        "1. Advance payment must be cleared before equipment pickup",
        "2. Equipment must be returned in original condition",
        "3. Any damages will incur additional charges",
        "4. Rental period starts from equipment pickup date",
        "5. Late returns will be charged extra"
    ]
    
    for term in terms:
        elements.append(Paragraph(term, normal_style))
    
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Thank you for choosing Agri-RentX!", normal_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

@login_required
def download_invoice(request, rental_id):
    """Download PDF invoice"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    try:
        pdf_content = generate_invoice_pdf(request, rental_id)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="agrirentx_invoice_{rental_id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating invoice: {str(e)}")
        return redirect('admin_dashboard')

@login_required
def send_invoice_email(request, rental_id):
    """Send invoice to user via email"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    rental = get_object_or_404(RentalRequest, id=rental_id)
    
    try:
        # Generate PDF
        pdf_content = generate_invoice_pdf(request, rental_id)
        
        # Send email with PDF attachment
        from django.core.mail import EmailMessage
        
        # Calculate amounts for email body using Decimal
        advance_amount = (rental.item.price_per_day * Decimal('0.5')).quantize(Decimal('0.01'))
        penalty_amount = rental.penalty_amount if rental.penalty_amount else Decimal('0')
        total_amount = advance_amount + penalty_amount
        
        email = EmailMessage(
            subject=f'Agri-RentX Invoice for {rental.item.name}',
            body=f"""
Dear {rental.user.username},

Thank you for renting with Agri-RentX!

Please find your invoice attached for the following rental:
- Equipment: {rental.item.name}
- Category: {rental.item.category}
- Advance Amount: ₹{advance_amount:.2f}
- Penalty Charges: ₹{penalty_amount:.2f}
- Total Amount: ₹{total_amount:.2f}
- Status: {rental.status.title()}

If you have any questions, please contact us.

Best regards,
Agri-RentX Team
            """,
            from_email=None,
            to=[rental.user.email],
        )
        
        email.attach(f'agrirentx_invoice_{rental_id}.pdf', pdf_content, 'application/pdf')
        email.send()
        
        messages.success(request, f"Invoice sent successfully to {rental.user.email}")
    
    except Exception as e:
        messages.error(request, f"Failed to send invoice: {str(e)}")
    
    return redirect('admin_dashboard')


# ------------------ ANALYTICS ------------------
@login_required
def admin_analytics(request):
    """Admin analytics dashboard"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    # Import here to avoid circular imports
    from .models import RentalRequest, AgricultureItem
    
    # Basic counts
    total_users = CustomUser.objects.filter(role='user').count()
    total_items = AgricultureItem.objects.count()
    total_rentals = RentalRequest.objects.count()
    
    # Status breakdowns - FIXED: Use correct fields
    user_status = CustomUser.objects.filter(role='user').values('status').annotate(count=Count('id'))
    
    # FIX: AgricultureItem doesn't have 'status' field, use 'is_available' instead
    item_status = AgricultureItem.objects.values('is_available').annotate(count=Count('id'))
    
    rental_status = RentalRequest.objects.values('status').annotate(count=Count('id'))
    
    # Revenue analytics - FIXED: Use Decimal for calculations
    total_revenue_result = RentalRequest.objects.filter(advance_paid=True).aggregate(
        total=Sum('item__price_per_day')
    )
    
    # Convert to Decimal and calculate 50% advance
    total_revenue = Decimal('0')
    if total_revenue_result['total']:
        total_revenue = (Decimal(str(total_revenue_result['total'])) * Decimal('0.5')).quantize(Decimal('0.01'))
    
    pending_payments = RentalRequest.objects.filter(
        terms_accepted=True, 
        advance_paid=False
    ).count()
    
    # Category analytics
    category_stats = AgricultureItem.objects.values('category').annotate(
        count=Count('id'),
        total_rentals=Count('rentalrequest')
    )
    
    # Recent activity
    recent_rentals = RentalRequest.objects.select_related('user', 'item').order_by('-request_date')[:10]
    
    # Additional analytics data
    approved_rentals = RentalRequest.objects.filter(status='approved').count()
    pending_rentals = RentalRequest.objects.filter(status='pending').count()
    
    # Calculate revenue by status
    revenue_by_status = {}
    for status in ['approved', 'pending', 'returned']:
        result = RentalRequest.objects.filter(
            status=status, 
            advance_paid=True
        ).aggregate(
            revenue=Sum('item__price_per_day')
        )
        revenue = Decimal('0')
        if result['revenue']:
            revenue = (Decimal(str(result['revenue'])) * Decimal('0.5')).quantize(Decimal('0.01'))
        revenue_by_status[status] = revenue
    
    context = {
        'total_users': total_users,
        'total_items': total_items,
        'total_rentals': total_rentals,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'user_status': list(user_status),
        'item_status': list(item_status),  # Now using is_available instead of status
        'rental_status': list(rental_status),
        'category_stats': list(category_stats),
        'recent_rentals': recent_rentals,
        'approved_rentals': approved_rentals,
        'pending_rentals': pending_rentals,
        'revenue_by_status': revenue_by_status,
        'now': timezone.now(),  # Add current time
    }
    
    return render(request, 'admin_analytics.html', context)


# ------------------ RETURN FUNCTIONALITY ------------------
@login_required
def return_rental(request, rental_id):
    """Handle rental return from user side"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    rental = get_object_or_404(RentalRequest, id=rental_id, user=request.user)
    
    # Check if rental can be returned
    if rental.status != 'approved':
        messages.error(request, "This rental cannot be returned.")
        return redirect('user_dashboard')
    
    if rental.is_returned:
        messages.info(request, "This item has already been returned.")
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        condition = request.POST.get('condition', 'good')
        notes = request.POST.get('notes', '')
        
        # Mark as returned
        rental.mark_as_returned(condition=condition, notes=notes)
        
        messages.success(request, f"Successfully returned {rental.item.name}. Thank you!")
        return redirect('user_dashboard')
    
    context = {
        'rental': rental,
    }
    return render(request, 'return_rental.html', context)

@login_required
def admin_process_return(request, rental_id):
    """Admin final processing of returned item"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    rental = get_object_or_404(RentalRequest, id=rental_id)
    
    if not rental.is_returned:
        messages.error(request, "This item has not been returned by the user yet.")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        # Admin can add final notes or adjust penalty
        penalty_amount = request.POST.get('penalty_amount', 0)
        admin_notes = request.POST.get('admin_notes', '')
        
        if penalty_amount:
            try:
                rental.penalty_amount = Decimal(penalty_amount)
                if Decimal(penalty_amount) > 0:
                    rental.status = 'damaged'  # Change status to damaged if penalty applied
            except (ValueError, InvalidOperation):
                messages.error(request, "Invalid penalty amount")
                return redirect('admin_process_return', rental_id=rental_id)
        
        if admin_notes:
            rental.admin_return_notes = admin_notes
        
        rental.save()
        
        # Calculate and show refund amount
        refund_amount = rental.calculate_refund_amount()
        if refund_amount > 0:
            messages.success(request, f"Return processed! Refund available: ₹{refund_amount}")
        else:
            messages.success(request, "Return processed! No refund available due to penalty.")
        
        return redirect('admin_dashboard')
    
    # Calculate potential refund amount for display
    refund_amount = rental.calculate_refund_amount()
    
    context = {
        'rental': rental,
        'refund_amount': refund_amount,
    }
    return render(request, 'admin_process_return.html', context)

# ------------------ REFUND PROCESSING (FIXED) ------------------
@login_required
def process_refund(request, rental_id):
    """Process 50% refund for returned rental"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    rental = get_object_or_404(RentalRequest, id=rental_id)
    
    # Check if rental can be refunded
    if not rental.is_returned:
        messages.error(request, "Item must be returned before processing refund.")
        return redirect('admin_dashboard')
    
    if rental.refund_processed:
        messages.info(request, "Refund already processed for this rental.")
        return redirect('admin_dashboard')
    
    # Calculate refund amount
    refund_amount = rental.calculate_refund_amount()
    
    if refund_amount <= 0:
        messages.warning(request, "No refund available due to penalty charges.")
        return redirect('admin_dashboard')
    
    # Process refund - FIXED: This was the main issue
    try:
        # Update rental status first
        rental.refund_processed = True
        rental.refund_amount = refund_amount
        rental.refund_date = timezone.now()
        rental.save()
        
        # Update user's wallet balance
        rental.user.wallet_balance += refund_amount
        rental.user.save()
        
        messages.success(request, f"Successfully refunded ₹{refund_amount} to {rental.user.username}'s wallet.")
        
    except Exception as e:
        messages.error(request, f"Failed to process refund: {str(e)}")
    
    return redirect('admin_dashboard')

@login_required
def user_wallet(request):
    """Display user's wallet balance and transaction history"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # Get user's rentals with refunds
    rentals_with_refunds = RentalRequest.objects.filter(
        user=request.user, 
        refund_processed=True
    ).order_by('-refund_date')
    
    context = {
        'wallet_balance': request.user.get_wallet_balance(),
        'refund_history': rentals_with_refunds,
        'now': timezone.now(),
    }
    return render(request, 'user_wallet.html', context)


# ------------------ NEW ITEMS NOTIFICATION ------------------
@login_required
def mark_notifications_read(request):
    """Mark new items notifications as read"""
    if request.user.role != 'user':
        messages.error(request, "Access denied")
        return redirect('user_signin')
    
    # Update user's last login to current time to mark notifications as read
    request.user.last_login = timezone.now()
    request.user.save()
    
    messages.success(request, "Notifications marked as read!")
    return redirect('user_dashboard')

# ------------------ ITEM MANAGEMENT ------------------
@login_required
def edit_item(request, item_id):
    """Edit agriculture item"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    item = get_object_or_404(AgricultureItem, id=item_id)
    
    if request.method == 'POST':
        form = AgricultureItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{item.name}' updated successfully!")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AgricultureItemForm(instance=item)
    
    context = {
        'form': form,
        'item': item,
        'is_edit': True,
    }
    return render(request, 'edit_item.html', context)

@login_required
def delete_item(request, item_id):
    """Delete agriculture item"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied")
        return redirect('admin_signin')
    
    item = get_object_or_404(AgricultureItem, id=item_id)
    item_name = item.name
    
    # Check if item has any rental requests
    has_rentals = RentalRequest.objects.filter(item=item).exists()
    
    if has_rentals:
        messages.error(request, f"Cannot delete '{item_name}' because it has rental requests. Mark it as unavailable instead.")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, f"Item '{item_name}' deleted successfully!")
        return redirect('admin_dashboard')
    
    context = {
        'item': item,
    }
    return render(request, 'delete_item_confirm.html', context)