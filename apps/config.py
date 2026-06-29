import os, random, string
from datetime import timedelta

class Config(object):

    basedir = os.path.abspath(os.path.dirname(__file__))

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static')  
    GA_MEASUREMENT_ID = os.getenv('GA_MEASUREMENT_ID', '').strip()
    GA_PROPERTY_ID = os.getenv('GA_PROPERTY_ID', '').strip()
    GA_CREDENTIALS_JSON = os.getenv('GA_CREDENTIALS_JSON', '').strip()
    GA_CREDENTIALS_FILE = os.getenv('GA_CREDENTIALS_FILE', '').strip()
    # Google Search Console: verifieringstoken (sätts i .env nar property skapas).
    # Tom = ingen tagg renderas. Behövs för att verifiera ägarskap + skicka in sitemap.
    GOOGLE_SITE_VERIFICATION = os.getenv('GOOGLE_SITE_VERIFICATION', '').strip()

    # Web-push (VAPID) for chatt-notiser i admin. Nycklar i .env. Tom = push av.
    VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '').strip()
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '').strip()
    VAPID_CLAIM_EMAIL = os.getenv('VAPID_CLAIM_EMAIL', 'mailto:info@1010monky.se').strip()

    # Admin-inloggning. Hash i .env (generera med werkzeug generate_password_hash).
    ADMIN_USER = os.getenv('ADMIN_USER', 'matias').strip()
    ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', '').strip()
    
    # Set up the App SECRET_KEY
    SECRET_KEY  = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice( string.ascii_lowercase  ) for i in range( 32 ))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DB_ENGINE   = os.getenv('DB_ENGINE'   , None)
    DB_USERNAME = os.getenv('DB_USERNAME' , None)
    DB_PASS     = os.getenv('DB_PASS'     , None)
    DB_HOST     = os.getenv('DB_HOST'     , None)
    DB_PORT     = os.getenv('DB_PORT'     , None)
    DB_NAME     = os.getenv('DB_NAME'     , None)

    USE_SQLITE  = True 

    # try to set up a Relational DBMS
    if DB_ENGINE and DB_NAME and DB_USERNAME:

        try:
            
            # Relational DBMS: PSQL, MySql
            SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
                DB_ENGINE,
                DB_USERNAME,
                DB_PASS,
                DB_HOST,
                DB_PORT,
                DB_NAME
            ) 

            USE_SQLITE  = False

        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )
            print('> Fallback to SQLite ')    

    if USE_SQLITE:

        # This will create a file in <app> FOLDER
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
    
class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True          # cookies bara over HTTPS (prod kor HTTPS)
    SESSION_COOKIE_SAMESITE = 'Lax'       # blockerar cross-site cookie-skick (CSRF-djupforsvar)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}
