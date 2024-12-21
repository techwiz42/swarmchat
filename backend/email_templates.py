# email_templates.py

VERIFICATION_EMAIL_TEMPLATE = """
Hello {username},

Welcome to SwarmChat! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you did not create this account, please ignore this email.

Best regards,
The SwarmChat Team
"""

PASSWORD_RESET_TEMPLATE = """
Hello {username},

You have requested to reset your SwarmChat password. Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
The SwarmChat Team
"""

def get_verification_email(username: str, verification_link: str) -> str:
    return VERIFICATION_EMAIL_TEMPLATE.format(
        username=username,
        verification_link=verification_link
    )

def get_password_reset_email(username: str, reset_link: str) -> str:
    return PASSWORD_RESET_TEMPLATE.format(
        username=username,
        reset_link=reset_link
    )
