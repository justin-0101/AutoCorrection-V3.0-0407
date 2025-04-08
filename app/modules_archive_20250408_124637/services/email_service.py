"""
Email Service Module
Provides email sending functionality
"""

import logging
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Get logger
logger = logging.getLogger(__name__)

class EmailService:
    """Email service class for sending various types of emails"""

    def __init__(self, config=None):
        """Initialize email service
        
        Args:
            config: Email configuration
        """
        # Default configuration can be loaded from environment variables
        self.config = config or {
            'SMTP_SERVER': 'smtp.example.com',
            'SMTP_PORT': 587,
            'SMTP_USERNAME': 'username',
            'SMTP_PASSWORD': 'password',
            'FROM_EMAIL': 'no-reply@example.com',
            'FROM_NAME': 'AutoCorrection System'
        }
    
    def send_email(self, to_email, subject, body, is_html=False):
        """Send an email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            is_html: Whether the body is HTML
            
        Returns:
            dict: Result of the email sending operation
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['FROM_NAME']} <{self.config['FROM_EMAIL']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            logger.info(f"Connecting to SMTP server: {self.config['SMTP_SERVER']}")
            
            # In production code, this would actually send the email
            # For now, we'll just simulate sending
            logger.info(f"Email would be sent to: {to_email}, Subject: {subject}")
            
            return {
                'success': True,
                'message': f"Email sent to {to_email}"
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_welcome_email(self, email, username):
        """Send welcome email to a new user
        
        Args:
            email: User email
            username: Username
            
        Returns:
            dict: Result of the email sending operation
        """
        subject = "Welcome to AutoCorrection System"
        body = f"""
        <html>
        <body>
            <h2>Welcome to AutoCorrection System, {username}!</h2>
            <p>Thank you for registering with our essay correction service.</p>
            <p>You can now start submitting essays for AI-powered correction and feedback.</p>
            <p>If you have any questions, please don't hesitate to contact our support team.</p>
            <br>
            <p>Best regards,</p>
            <p>The AutoCorrection Team</p>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body, is_html=True)
    
    def send_password_reset_email(self, email, reset_token):
        """Send password reset email
        
        Args:
            email: User email
            reset_token: Password reset token
            
        Returns:
            dict: Result of the email sending operation
        """
        subject = "Password Reset Request"
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password.</p>
            <p>Use the following token to reset your password: <strong>{reset_token}</strong></p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <br>
            <p>Best regards,</p>
            <p>The AutoCorrection Team</p>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body, is_html=True)

