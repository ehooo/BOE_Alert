from boe.utils import cargar_conf, get_mongo_uri, FICHERO_CONFIGURACION
CONF = cargar_conf(FICHERO_CONFIGURACION)

BROKER_URL = get_mongo_uri(CONF)

CELERYD_CONCURRENCY = CONF.getint("celery","simultaneos")
CELERY_IMPORTS = ("boe.processing", )
#CELERY_INCLUDE = ("tasks", )

CELERYD_LOG_FORMAT = CONF.get("celery","formato_log").replace('$','%')
CELERYD_TASK_LOG_FORMAT = CONF.get("celery","formato_log_tareas").replace('$','%')

CELERY_REDIRECT_STDOUTS_LEVEL = CONF.get('log', "nivel")

CELERY_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": CONF.get("db","host"),
    "port": CONF.getint("db","puerto"),
    "database": CONF.get("db","nombre"),
    "taskmeta_collection": CONF.get("celery","meta"),
	"max_pool_size": CELERYD_CONCURRENCY+1
}

'''
# Enables error emails.
CELERY_SEND_TASK_ERROR_EMAILS = True
# Name and email addresses of recipients
ADMINS = (
    ("Admin Name", "admin@example.com"),
)
# Email address used as sender (From field).
SERVER_EMAIL = "no-reply@example.com"
# Mailserver configuration
EMAIL_HOST = "mail.example.com"
EMAIL_PORT = 25
# EMAIL_HOST_USER = "servers"
# EMAIL_HOST_PASSWORD = "s3cr3t"
#'''
