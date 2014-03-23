from boe.utils import cargar_conf, get_mongo_uri, FICHERO_CONFIGURACION

CONF = cargar_conf(FICHERO_CONFIGURACION)
try:
	BROKER_VHOST = CONF.get("db","nombre")
except:
	pass

#'''
BROKER_URL = get_mongo_uri(CONF)
CELERY_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": CONF.get("db","host"),
    "port": CONF.getint("db","puerto"),
    "database": CONF.get("db","nombre"),
    "taskmeta_collection": CONF.get("celery","meta"),
	"max_pool_size": CONF.getint("celery","pool")
}
#'''

CELERYD_CONCURRENCY = CONF.getint("celery","simultaneos")
CELERY_IMPORTS = ("boe.processing", )

CELERYD_LOG_FORMAT = CONF.get("celery","formato_log").replace('$','%')
CELERYD_TASK_LOG_FORMAT = CONF.get("celery","formato_log_tareas").replace('$','%')
CELERY_REDIRECT_STDOUTS_LEVEL = CONF.get('log', "nivel")

CELERY_IGNORE_RESULT = True
CELERY_TASK_RESULT_EXPIRES=1 #Cada segundo se eliminan los resultados
CELERY_MAX_CACHED_RESULTS=100 #Mantine un maximo de 100 resultados
