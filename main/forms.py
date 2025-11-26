from django import forms
from .models import CustomUser, AgricultureItem, RentalRequest
from decimal import Decimal

# ---------- User/Admin Signup ----------
# ---------- User/Admin Signup ----------
class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'address']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your complete address'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'user'
        user.status = 'approved'  # Auto-approve for testing, you can change this
        if commit:
            user.save()
        return user


# ---------- OTP Forms ----------
class OTPRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Enter your username'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Enter your email'
        })
    )


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=7, 
        required=True, 
        help_text="Enter 7-digit OTP",
        widget=forms.TextInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Enter 7-digit OTP',
            'pattern': '[0-9]{7}',
            'maxlength': '7'
        })
    )


# ---------- Agriculture Item Form ----------
class AgricultureItemForm(forms.ModelForm):
    class Meta:
        model = AgricultureItem
        fields = ['name', 'category', 'description', 'price_per_day', 'image', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'amazon-form-control',
                'placeholder': 'Enter item name'
            }),
            'category': forms.Select(attrs={
                'class': 'amazon-form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'amazon-form-control',
                'rows': 3,
                'placeholder': 'Enter item description'
            }),
            'price_per_day': forms.NumberInput(attrs={
                'class': 'amazon-form-control',
                'placeholder': 'Enter price per day',
                'step': '0.01',
                'min': '0'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'amazon-form-control'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'image': 'Upload a clear image of the item (JPG, PNG, WEBP)',
            'price_per_day': 'Enter the daily rental price in ₹',
        }

    def clean_price_per_day(self):
        price_per_day = self.cleaned_data.get('price_per_day')
        if price_per_day and price_per_day <= 0:
            raise forms.ValidationError("Price must be greater than 0")
        return price_per_day

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and len(name) < 3:
            raise forms.ValidationError("Item name must be at least 3 characters long")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError("Description must be at least 10 characters long")
        return description


# ---------- Admin: User Status Form ----------
class UserStatusForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'amazon-form-control'
            })
        }


# ---------- Admin: Rental Request Status Form ----------
class RentalStatusForm(forms.ModelForm):
    class Meta:
        model = RentalRequest
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'amazon-form-control'
            })
        }


# ---------- Admin: Rental Management (New) ----------
class RentalManagementForm(forms.ModelForm):
    """
    Admin can update rental details like:
    - Status (approve/reject/returned/damaged)
    - Damage report
    - Penalty amount
    """
    class Meta:
        model = RentalRequest
        fields = ['status', 'damage_report', 'penalty_amount']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'amazon-form-control'
            }),
            'damage_report': forms.Textarea(attrs={
                'class': 'amazon-form-control',
                'rows': 3, 
                'placeholder': 'Describe any damage...'
            }),
            'penalty_amount': forms.NumberInput(attrs={
                'class': 'amazon-form-control',
                'placeholder': 'Enter penalty amount (if any)',
                'step': '0.01',
                'min': '0'
            }),
        }

    def clean_penalty_amount(self):
        penalty_amount = self.cleaned_data.get('penalty_amount')
        if penalty_amount and penalty_amount < 0:
            raise forms.ValidationError("Penalty amount cannot be negative")
        return penalty_amount


# ---------- User: Terms Acceptance Form ----------
class TermsAcceptanceForm(forms.ModelForm):
    """
    User accepts terms and completes payment step.
    """
    agree = forms.BooleanField(
        required=True, 
        label="I agree to the terms and conditions",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = RentalRequest
        fields = ['terms_accepted', 'advance_paid', 'payment_reference']
        widgets = {
            'payment_reference': forms.TextInput(attrs={
                'class': 'amazon-form-control',
                'placeholder': 'Enter payment transaction ID'
            })
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.terms_accepted = True
        instance.advance_paid = True
        if not instance.payment_reference:
            instance.payment_reference = "TXN" + str(instance.id).zfill(6)
        if commit:
            instance.save()
        return instance


# ---------- Aadhaar Verification Form (NEW) ----------
class AadhaarVerificationForm(forms.ModelForm):
    """
    Users upload Aadhaar documents for address verification
    Only government authorized documents accepted
    """
    aadhaar_number = forms.CharField(
        max_length=12,
        min_length=12,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'amazon-form-control',
            'pattern': '[0-9]{12}',
            'title': 'Enter 12-digit Aadhaar number',
            'placeholder': '123456789012'
        }),
        help_text="Enter 12-digit Aadhaar number without spaces"
    )
    
    class Meta:
        model = CustomUser
        fields = ['aadhaar_number', 'aadhaar_front', 'aadhaar_back']
        widgets = {
            'aadhaar_front': forms.FileInput(attrs={
                'class': 'amazon-form-control',
                'accept': 'image/*,.jpg,.jpeg,.png,.pdf',
                'required': 'true'
            }),
            'aadhaar_back': forms.FileInput(attrs={
                'class': 'amazon-form-control', 
                'accept': 'image/*,.jpg,.jpeg,.png,.pdf',
                'required': 'true'
            }),
        }
        labels = {
            'aadhaar_front': 'Aadhaar Front Side',
            'aadhaar_back': 'Aadhaar Back Side'
        }
        help_texts = {
            'aadhaar_front': 'Upload clear image of Aadhaar front side (Max 5MB)',
            'aadhaar_back': 'Upload clear image of Aadhaar back side (Max 5MB)'
        }
    
    def clean_aadhaar_number(self):
        aadhaar_number = self.cleaned_data['aadhaar_number']
        # Remove any spaces or dashes
        aadhaar_number = aadhaar_number.strip().replace(' ', '').replace('-', '')
        
        if not aadhaar_number.isdigit():
            raise forms.ValidationError("Aadhaar number must contain only digits")
        
        if len(aadhaar_number) != 12:
            raise forms.ValidationError("Aadhaar number must be exactly 12 digits")
        
        # Check if Aadhaar number already exists for other users
        if CustomUser.objects.filter(aadhaar_number=aadhaar_number).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This Aadhaar number is already registered with another account")
        
        return aadhaar_number
    
    def clean_aadhaar_front(self):
        aadhaar_front = self.cleaned_data.get('aadhaar_front')
        if aadhaar_front:
            # Check file size (max 5MB)
            if aadhaar_front.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 5MB")
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            extension = aadhaar_front.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("Only JPG, PNG, and PDF files are allowed")
        
        return aadhaar_front
    
    def clean_aadhaar_back(self):
        aadhaar_back = self.cleaned_data.get('aadhaar_back')
        if aadhaar_back:
            # Check file size (max 5MB)
            if aadhaar_back.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 5MB")
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            extension = aadhaar_back.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("Only JPG, PNG, and PDF files are allowed")
        
        return aadhaar_back


# ---------- Return Item Form (NEW) ----------
class ReturnItemForm(forms.ModelForm):
    """
    Form for users to return rented items
    """
    condition_choices = [
        ('excellent', 'Excellent - No visible damage'),
        ('good', 'Good - Minor wear and tear'),
        ('damaged', 'Damaged - Significant damage or issues'),
    ]
    
    return_condition = forms.ChoiceField(
        choices=condition_choices,
        widget=forms.Select(attrs={
            'class': 'amazon-form-control'
        }),
        help_text="Select the condition of the returned item"
    )
    
    return_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'amazon-form-control',
            'rows': 3,
            'placeholder': 'Add any additional notes about the item condition...'
        }),
        help_text="Optional: Add any notes about the item's condition"
    )

    class Meta:
        model = RentalRequest
        fields = ['return_condition', 'return_notes']


# ---------- Refund Processing Form (NEW) ----------
class RefundProcessingForm(forms.ModelForm):
    """
    Admin form for processing refunds
    """
    refund_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'amazon-form-control',
            'step': '0.01',
            'min': '0'
        }),
        help_text="Enter the refund amount to be processed"
    )
    
    refund_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'amazon-form-control',
            'rows': 3,
            'placeholder': 'Add notes about the refund processing...'
        }),
        help_text="Optional: Add notes about this refund"
    )

    class Meta:
        model = RentalRequest
        fields = ['refund_amount', 'refund_notes']

    def clean_refund_amount(self):
        refund_amount = self.cleaned_data.get('refund_amount')
        if refund_amount and refund_amount < 0:
            raise forms.ValidationError("Refund amount cannot be negative")
        
        # Check if refund amount is reasonable (not more than advance paid)
        if hasattr(self.instance, 'calculate_advance_amount'):
            max_refund = self.instance.calculate_advance_amount()
            if refund_amount > max_refund:
                raise forms.ValidationError(f"Refund amount cannot exceed the advance paid (₹{max_refund})")
        
        return refund_amount


# ---------- Stock Notification Form (NEW) ----------
class StockNotificationForm(forms.Form):
    """
    Form for users to request stock notifications
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Enter your email for notifications'
        }),
        help_text="We'll notify you when this item is back in stock"
    )
    
    notify_when_available = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Notify me when this item is available"
    )


# ---------- Contact Form (NEW) ----------
class ContactForm(forms.Form):
    """
    Contact form for user inquiries
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Your email address'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'amazon-form-control',
            'placeholder': 'Subject of your message'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'amazon-form-control',
            'rows': 5,
            'placeholder': 'Your message...'
        })
    )
    urgency = forms.ChoiceField(
        choices=[
            ('low', 'Low Priority'),
            ('medium', 'Medium Priority'),
            ('high', 'High Priority'),
        ],
        widget=forms.Select(attrs={
            'class': 'amazon-form-control'
        }),
        initial='medium'
    )


# ---------- Bulk Item Upload Form (NEW) ----------
class BulkItemUploadForm(forms.Form):
    """
    Form for admin to upload multiple items via CSV
    """
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'amazon-form-control',
            'accept': '.csv'
        }),
        help_text="Upload a CSV file with columns: name, category, description, price_per_day"
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Overwrite existing items with same names",
        help_text="If checked, existing items with the same names will be updated"
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError("Only CSV files are allowed")
            
            # Check file size (max 10MB)
            if csv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB")
        
        return csv_file


# ---------- Price Update Form (NEW) ----------
class PriceUpdateForm(forms.Form):
    """
    Form for bulk price updates
    """
    percentage_change = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'amazon-form-control',
            'step': '0.01',
            'placeholder': 'Enter percentage change'
        }),
        help_text="Enter percentage to increase (positive) or decrease (negative) prices"
    )
    
    categories = forms.MultipleChoiceField(
        choices=AgricultureItem.CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        help_text="Select categories to update (leave empty for all categories)"
    )
    
    apply_to_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Apply to all items in selected categories"
    )

    def clean_percentage_change(self):
        percentage_change = self.cleaned_data.get('percentage_change')
        if percentage_change and percentage_change < -100:
            raise forms.ValidationError("Price cannot be decreased by more than 100%")
        return percentage_change