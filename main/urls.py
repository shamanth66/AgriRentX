from django.urls import path
from . import views

urlpatterns = [
    # Landing and info pages
    path('', views.landing_page, name='landing'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    
    # Authentication
    path('logout/', views.logout_view, name='logout'),
    
    # User authentication
    path('user/signup/', views.user_signup, name='user_signup'),
    path('user/signin/', views.user_signin, name='user_signin'),
    path('user/verify-otp/', views.user_verify_otp, name='user_verify_otp'),
    
    # Admin authentication (simplified)
    path('admin/signin/', views.admin_signin, name='admin_signin'),
    
    # Dashboards
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Aadhaar verification
    path('aadhaar/verification/', views.aadhaar_verification, name='aadhaar_verification'),
    
    # Rental process
    path('rental/terms/<int:item_id>/', views.rental_terms, name='rental_terms'),
    path('rental/accept-terms/<int:item_id>/', views.accept_terms, name='accept_terms'),
    path('rental/payment/<int:rental_id>/', views.rental_payment, name='rental_payment'),
    path('rental/process-payment/<int:rental_id>/', views.process_payment, name='process_payment'),
    
    # Admin actions
    path('admin/user/<int:user_id>/status/<str:status>/', views.change_user_status, name='change_user_status'),
    path('admin/item/<int:item_id>/toggle-availability/', views.change_item_availability, name='change_item_availability'),
    path('admin/rental/<int:rental_id>/status/<str:status>/', views.change_rental_status, name='change_rental_status'),
    path('admin/rental/<int:rental_id>/update-damage/', views.update_rental_damage, name='update_rental_damage'),
    
    # Aadhaar admin actions
    path('admin/verify-aadhaar/<int:user_id>/', views.verify_aadhaar, name='verify_aadhaar'),
    path('admin/reject-aadhaar/<int:user_id>/', views.reject_aadhaar, name='reject_aadhaar'),
    
    # Invoice and analytics
    path('admin/invoice/download/<int:rental_id>/', views.download_invoice, name='download_invoice'),
    path('admin/invoice/email/<int:rental_id>/', views.send_invoice_email, name='send_invoice_email'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('return-rental/<int:rental_id>/', views.return_rental, name='return_rental'),
    path('admin/process-return/<int:rental_id>/', views.admin_process_return, name='admin_process_return'),
    path('admin/process-refund/<int:rental_id>/', views.process_refund, name='process_refund'),
    path('user/wallet/', views.user_wallet, name='user_wallet'),
    
    # Notification URLs
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notify-when-available/<int:item_id>/', views.notify_when_available, name='notify_when_available'),
    path('remove-stock-notification/<int:notification_id>/', views.remove_stock_notification, name='remove_stock_notification'),
    path('admin/edit-item/<int:item_id>/', views.edit_item, name='edit_item'),
    path('admin/delete-item/<int:item_id>/', views.delete_item, name='delete_item'),
]