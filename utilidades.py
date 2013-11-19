'''
Funcioles utiles miscelaneas
'''
import os
ESTE_DIRECTORIO = os.path.dirname(__file__)

import ConfigParser, logging
def cargar_conf():
	conf = ConfigParser.ConfigParser()
	conf.readfp(open(ESTE_DIRECTORIO + "/configuracion.conf"))

	logging.basicConfig(format=conf.get("log", "formato").replace('$','%'))

	NIVELES = {'DEBUG': logging.DEBUG,
			  'INFO': logging.INFO,
			  'WARNING': logging.WARNING,
			  'ERROR': logging.ERROR,
			  'CRITICAL': logging.CRITICAL}
	logging.getLogger().setLevel( NIVELES[ conf.get("log", "nivel") ] )
	return conf

try:
	#Para Linux
	from pymongo.bson import ObjectId
except:
	#Para Windows
	from bson.objectid import ObjectId

def cifrar_id(id, usuario):
	return str(id)
def descifrar_id(cid, usuario):
	return ObjectId(cid)

def get_mongo_uri(conf):
	credencial = ""
	if conf.has_option("db", "usuario") and conf.has_option("db", "clave"):
		credencial = "%(usuario)s:%(clave)s@" % {
			"usuario":	conf.get("db", "usuario"),
			"clave":	conf.get("db", "clave")
		}
	return 'mongodb://%(credencial)s%(host)s:%(puerto)s/%(nombre_db)s'%{
		"credencial": credencial,
		"host": conf.get("db", "host"),
		"puerto": conf.get("db","puerto"),
		"nombre_db": conf.get("db","nombre"),
	}

	
