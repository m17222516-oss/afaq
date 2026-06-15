import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from database.db import add_policies_table, init_db
from routes.admin import admin_bp
from routes.announcements import announcements_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.policies import policies_bp

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ============================================================
# FILE UPLOAD CONFIGURATION
# ============================================================
# Increase maximum file upload size to 16 MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Optional: Additional upload settings
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

# Ensure upload directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("static/uploads/announcements", exist_ok=True)

# ============================================================
# ERROR HANDLERS
# ============================================================


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash("حجم الملف كبير جداً. الحد الأقصى هو 16 ميجابايت.", "danger")
    return redirect(request.url)


@app.errorhandler(404)
def not_found(e):
    """Handle 404 error"""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 error"""
    flash("حدث خطأ في الخادم. الرجاء المحاولة مرة أخرى.", "danger")
    return redirect(url_for("dashboard.index"))


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(announcements_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(policies_bp)


# ============================================================
# CONTEXT PROCESSOR
# ============================================================
@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""

    def get_current_year():
        import datetime

        return datetime.datetime.now().year

    return dict(current_year=get_current_year())


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    # Initialize database
    init_db()
    add_policies_table()

    # Run the app
    # Use host='0.0.0.0' to allow external access
    # Use debug=False for production
    app.run(debug=True, host="0.0.0.0", port=5000)
