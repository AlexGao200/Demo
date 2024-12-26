from flask import Blueprint, jsonify, request, current_app
from flask_mail import Message as MailMessage

from loguru import logger


def create_misc_blueprint(email_service):
    misc_bp = Blueprint("misc", __name__, url_prefix="/api")

    @misc_bp.route("/contact", methods=["POST"])
    def contact_us():
        try:
            data = request.get_json()
            name = data.get("name")
            email = data.get("email")
            message = data.get("message")

            if not name or not email or not message:
                return jsonify({"error": "All fields are required"}), 400

            # Construct the email message with the authenticated sender
            msg = MailMessage(
                subject=f"Contact Us Message from {name}",
                sender=current_app.config["MAIL_DEFAULT_SENDER"],
                recipients=["info@acaceta.com"],
                body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
            )

            # Send the email
            email_service.send(msg)

            logger.info(f"Contact message sent successfully by {name} ({email})")
            return jsonify({"message": "Message sent successfully"}), 200

        except Exception as e:
            logger.error(f"Error sending contact message: {e}")
            return jsonify({"error": "Failed to send message", "details": str(e)}), 500

    @misc_bp.route("/")
    def index():
        return jsonify({"message": "API is working"}), 200

    return misc_bp
