from utils import get_mongo_uri

from pymongo import Connection
import logging

class DBConnector():
	def __init__(self, conf):
		nombre_db = conf.get("db", "nombre")
		url_conexion = get_mongo_uri(conf)
		self.conexion = Connection(url_conexion, conf.getint("db", "puerto"))
		self.db = self.conexion[nombre_db]

class DBObject(object):
	def __init__(self, dbConnector):
		assert isinstance(dbConnector, DBConnector)
		self._orig_conn = dbConnector
		self.db = dbConnector.db
		self.id = None
		self.to_save_data = {}
	def __setitem__(self, key, value):
		if key in ["_id", "id"]:
			res = self.getConexion().find_one({"_id":value}, fields=["_id"])
			if res and "_id" in res:
				self.id = res["_id"]
			else:
				logging.debug("ID Desconocido %s: %s"%(self.__class__.__name__, value))
		elif self.id:
			self.getConexion().update({"_id":self.id}, {'$set':{key:value}})
		else:
			self.to_save_data[key] = value
	def __getitem__(self, key):
		ret = None
		if key in ['_id','id']:
			ret = self.id
		elif self.id:
			try:
				ret = self.getConexion().find_one({"_id":self.id}, fields=[key])
				if ret and key in ret:
					ret = ret[key]
				else:
					ret = None
			except TypeError:
				logging.error("Error con la clave '%s'"%key)
		elif key in self.to_save_data:
			ret = self.to_save_data[key]
		return ret
	def __contains__(self, item):
		ret = False
		if self.id:
			exist = self.getConexion().find_one({"_id":self.id}, fields=[item])
			if exist is not None and item in exist:
				ret = True
		elif item in self.to_save_data:
			ret = True
		return ret
	def getConexion(self):
		return self.db[self.__class__.__name__]
	def save(self, force=False):
		if len(self.to_save_data)>0:
			if self.id:
				self.getConexion().update({"_id":self.id}, {'$set':self.to_save_data})
			else:
				self.id = self.getConexion().insert(self.to_save_data)
			self.to_save_data = {}
	def list(self, page=0, filter={}, sort=[], count=10):
		ret = {
			'page':page,
			'total':0,
			'data':[]
		}
		res = self.getConexion().find(filter, sort=sort, fields=["_id"])
		ret['total'] = res.count()
		items = res.skip(page*count).limit(count)
		for i in items:
			s = self.__new__(self.__class__)
			s.__init__(self._orig_conn)
			s.id = i["_id"]
			ret['data'].append(s)
		return ret
	def remove(self):
		if self.id:
			self.getConexion().remove({'_id':self.id})

from datetime import timedelta
class Usuario(DBObject):
	def remove(self):
		if self.id:
			Alertas(self._orig_conn).getConexion().remove({'usuario':self.id})
			Regla(self._orig_conn).getConexion().remove({'usuario':self.id})
		DBObject.remove(self)
	def clean_alertas(self):
		if self.id:
			alertas = Alertas(self._orig_conn)
			ultima = alertas.list(0, {'usuario':self.id}, [('fecha',-1)], 1)
			dias = self['clean_dias']
			if not dias:
				dias = 5
			if len(ultima['data']) > 0:
				borrar = ultima['data'][0]['fecha'] - timedelta(dias)
				alertas.getConexion().remove({'usuario':self.id, 'fecha':{'$lt':borrar}})

class Alertas(DBObject):
	def add(self, regla, boe, fecha):
		assert regla is None or isinstance(regla, Regla) or regla.id is None
		res = self.getConexion().find_one({'usuario':regla['usuario'],'boe':boe}, fields=["_id"])
		push_id = None
		if res and "_id" in res:
			push_id = res["_id"]
		else:
			push_id = self.getConexion().insert({'usuario':regla['usuario'], 'boe':boe, 'fecha':fecha})
		if push_id:
			self.getConexion().update({ '_id':push_id, 'alias':{"$ne":regla['alias']}}, {"$push":{'alias':regla['alias']}} )
			ret = self.__new__(self.__class__)
			ret.__init__(self._orig_conn)
			ret.id = push_id
			return ret

class PalagraClave(DBObject):
	def __init__(self, dbConnector, palabras_clave=["seccion","departamento","epigrafe","origen_legislativo","materia","alerta","materias_cpv"]):
		DBObject.__init__(self, dbConnector)
		self.psc = palabras_clave
	def __setitem__(self, key, value):
		if key in self.psc:
			value = value.lower()
			if value.strip() == "":
				self.id =  None
				return
			res = self.getConexion().find_one({key:value}, fields=["_id"])
			if res and "_id" in res:
				self.id = res["_id"]
			else:
				self.id = None
				self.to_save_data[key] = value
				self.save()
		else:
			DBObject.__setitem__(self, key, value)
	def getTipo(self):
		for key in self.psc:
			if key in self:
				return key
	def __str__(self):
		key = self.getTipo()
		if key is not None:
			return self[key].encode('utf-8','replace')
		return ""
		return DBObject.__str__(self)

class Regla(DBObject):
	def __init__(self, db):
		DBObject.__init__(self, db)
	def add_rule_S(self, usuario, alias, seccion=None, departamento=None, epigrafe=None, re_titulo=None):
		assert isinstance(usuario, Usuario)
		assert alias is not None
		assert seccion is None or isinstance(seccion, PalagraClave)
		assert departamento is None or isinstance(departamento, PalagraClave)
		assert epigrafe is None or isinstance(epigrafe, PalagraClave)

		ret = self.__new__(self.__class__)
		ret.__init__(self._orig_conn)
		ret["tipo"] = 'S'
		ret['usuario'] = usuario.id
		ret['alias'] = alias
		if seccion is not None:
			ret['seccion'] = seccion.id
		if departamento is not None:
			ret['departamento'] = departamento.id
		if epigrafe is not None:
			ret['epigrafe'] = epigrafe.id
		if re_titulo is not None:
			ret['re_titulo'] = re_titulo
		ret.save()
		return ret
	def add_rule_A(self, usuario, alias, malformado=None, re_titulo=None, departamento=None, origen_legislativo=None, materias=None, alertas=None, re_texto=None):
		assert isinstance(usuario, Usuario)
		assert alias is not None
		assert departamento is None or isinstance(departamento, PalagraClave)
		assert origen_legislativo is None or isinstance(origen_legislativo, PalagraClave)
		assert materias is None or isinstance(materias, PalagraClave)
		assert alertas is None or isinstance(alertas, PalagraClave)

		ret = self.__new__(self.__class__)
		ret.__init__(self._orig_conn)
		ret["tipo"] = 'A'
		ret['usuario'] = usuario.id
		ret['alias'] = alias
		if malformado is not None:
			if malformado:
				ret['malformado'] = True
			else:
				ret['malformado'] = False
		if re_titulo is not None:
			ret['re_titulo'] = re_titulo
		if departamento is not None:
			ret['departamento'] = departamento.id
		if origen_legislativo is not None:
			ret['origen_legislativo'] = origen_legislativo.id
		if materias is not None:
			ret['materia'] = materias.id
		if alertas is not None:
			ret['alerta'] = alertas.id
		if re_texto is not None:
			ret['re_texto'] = re_texto
		ret.save()
		return ret
	def add_rule_B(self, usuario, alias, malformado=False, re_titulo=None, materias_cpv=None, departamento=None, re_texto=None):
		assert isinstance(usuario, Usuario)
		assert alias is not None
		assert departamento is None or isinstance(departamento, PalagraClave)

		ret = self.__new__(self.__class__)
		ret.__init__(self._orig_conn)
		ret['usuario'] = usuario.id
		ret['alias'] = alias
		ret['tipo'] = 'B'
		if malformado is not None:
			if malformado:
				ret['malformado'] = True
			else:
				ret['malformado'] = False
		if re_titulo is not None:
			ret['re_titulo'] = re_titulo
		if departamento is not None:
			ret['departamento'] = departamento.id
		if re_texto is not None:
			ret['re_texto'] = re_texto
		ret.save()
		return ret
