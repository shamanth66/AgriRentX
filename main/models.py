from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from decimal import Decimal

# ---------- Custom User ----------
class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, role='user', **extra_fields):
        if not username or not email:
            raise ValueError("Username and email are required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_unusable_password()  # OTP-only
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, role='admin', **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('admin', 'Admin'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Aadhaar Verification Fields
    aadhaar_number = models.CharField(max_length=12, blank=True, null=True)
    aadhaar_front = models.ImageField(upload_to='aadhaar/', blank=True, null=True)
    aadhaar_back = models.ImageField(upload_to='aadhaar/', blank=True, null=True)
    is_aadhaar_verified = models.BooleanField(default=False)
    aadhaar_verification_date = models.DateTimeField(blank=True, null=True)

    # Wallet balance for refunds
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f"{self.username} ({self.role})"

    def add_to_wallet(self, amount):
        """Add amount to user's wallet"""
        self.wallet_balance += Decimal(amount)
        self.save()

    def get_wallet_balance(self):
        """Get user's wallet balance"""
        return self.wallet_balance


# ---------- Stock Notification Model ----------
class StockNotification(models.Model):
    """Model for back-in-stock notifications"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    item = models.ForeignKey('AgricultureItem', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'item']
    
    def __str__(self):
        return f"{self.user.username} - {self.item.name}"


# ---------- Agriculture Items ----------
class AgricultureItem(models.Model):
    CATEGORY_CHOICES = (
        ('Lawn & Gardening', 'Lawn & Gardening'),
        ('Hand Tools', 'Hand Tools'),
        ('Earth Auger', 'Earth Auger'),
        ('Ploughs', 'Ploughs'),
        ('Seeders', 'Seeders'),
        ('Sprayers', 'Sprayers'),
        ('Fertilizers', 'Fertilizers'),
    )

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    added_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    # Fields for new item notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_new = models.BooleanField(default=True)
    new_until = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def save(self, *args, **kwargs):
        # If this is a new item being created, mark it as new
        if not self.pk:
            self.is_new = True
            self.new_until = timezone.now() + timezone.timedelta(days=7)  # New for 7 days
        
        # If item becomes available, notify subscribed users
        if self.pk:
            old_item = AgricultureItem.objects.get(pk=self.pk)
            if not old_item.is_available and self.is_available:
                self.notify_subscribed_users()
        
        super().save(*args, **kwargs)
    
    def notify_subscribed_users(self):
        """Notify users who subscribed for back-in-stock notifications"""
        from django.core.mail import send_mail
        
        notifications = StockNotification.objects.filter(item=self, notified=False)
        for notification in notifications:
            try:
                send_mail(
                    subject=f'{self.name} is Back in Stock! - AgriRentX',
                    message=f'Hello {notification.user.username},\n\nGood news! The equipment "{self.name}" you were interested in is now back in stock and available for rental.\n\nVisit AgriRentX to rent it now before it gets taken!\n\nBest regards,\nAgriRentX Team',
                    from_email=None,
                    recipient_list=[notification.user.email],
                    fail_silently=False,
                )
                notification.notified = True
                notification.save()
            except Exception as e:
                print(f"Failed to send notification to {notification.user.email}: {e}")


# ---------- Rental Requests ----------
class RentalRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned'),
        ('damaged', 'Damaged'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rental_requests')
    item = models.ForeignKey(AgricultureItem, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    terms_accepted = models.BooleanField(default=False)
    advance_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    damage_report = models.TextField(blank=True, null=True)
    penalty_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Return functionality fields
    return_date = models.DateTimeField(blank=True, null=True)
    is_returned = models.BooleanField(default=False)
    return_condition = models.CharField(max_length=20, choices=(
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('damaged', 'Damaged'),
    ), blank=True, null=True)
    return_notes = models.TextField(blank=True, null=True)
    admin_return_notes = models.TextField(blank=True, null=True)
    
    # Refund fields
    refund_processed = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    refund_date = models.DateTimeField(blank=True, null=True)
    
    # Deadline notification field
    deadline_notification_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} requests {self.item.name} ({self.status})"
    
    def calculate_advance_amount(self):
        """Calculate 50% advance amount"""
        return (self.item.price_per_day * Decimal('0.5')).quantize(Decimal('0.01'))
    
    def calculate_refund_amount(self):
        """Calculate 50% refund amount (50% of advance)"""
        if self.penalty_amount and self.penalty_amount > 0:
            # If there's penalty, subtract it from refund
            refund = (self.calculate_advance_amount() * Decimal('0.5')) - self.penalty_amount
            return max(refund, Decimal('0'))  # Ensure refund is not negative
        else:
            # Normal refund: 50% of advance (which is 25% of daily rate)
            return (self.calculate_advance_amount() * Decimal('0.5')).quantize(Decimal('0.01'))
    
    def days_until_deadline(self):
        """Calculate days until rental deadline (7 days from approval)"""
        if self.status != 'approved' or not self.advance_paid:
            return None
        
        # Assuming rental period is 7 days from approval
        approval_date = self.request_date  # Using request_date as approval date for simplicity
        deadline = approval_date + timezone.timedelta(days=7)
        days_left = (deadline - timezone.now()).days
        
        return max(days_left, 0)
    
    def mark_as_returned(self, condition="good", notes=""):
        """Mark rental as returned"""
        self.is_returned = True
        self.return_date = timezone.now()
        self.return_condition = condition
        self.return_notes = notes
        self.status = 'returned'
        self.save()
        
        # Make the item available again
        self.item.is_available = True
        self.item.save()
        
        # Calculate refund amount
        refund_amount = self.calculate_refund_amount()
        self.refund_amount = refund_amount
        self.save()

    def process_refund(self):
        """Process refund to user's wallet"""
        if not self.refund_processed and self.refund_amount and self.refund_amount > 0:
            self.user.add_to_wallet(self.refund_amount)
            self.refund_processed = True
            self.refund_date = timezone.now()
            self.save()
            return True
        return False

    class Meta:
        ordering = ['-request_date']