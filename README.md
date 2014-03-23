# Licencia
Copyright (C) 2013 [ehooo](https://github.com/ehooo)

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Acerca de:
Sistema de procesado y alertar para el BOE (Boletin Oficial del Estado).<br/>
Consta de dos scripts principales:

* pagina.py: Aplicacion para WebPy que permite insertar reglas y configurar el modo de alerta.
* scan.py: Que procesa el BOE de un dia dado, o el ultimo publicado.

El programa `scan.py` se encarga de procesar el BOE haciendo uso de 
ficheros xml del [portal oficial](http://boe.es/diario_boe/) y 
comparandolos con expresiones regurales y otros filtros.

# Instalar
* [python](http://www.python.org/download/): `# apt-get install python`
 * [easy\_install](https://pypi.python.org/pypi/setuptools): `# apt-get install python-pip`
* [mongoDB](http://www.mongodb.org/downloads): `# apt-get install mongodb-server`
<pre>
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
sudo apt-get update
sudo apt-get install mongodb-10gen=2.4.8
sudo /etc/init.d/mongodb status
</pre>
* [pymongo](http://api.mongodb.org/python/current/installation.html): `# apt-get install python-pymongo` o `# easy_install pymongo`
* [web.py](http://webpy.org/install): `# easy_install web.py`
* [Celery](http://www.celeryproject.org/install/): `# easy_install Celery`
* [Twython](https://twython.readthedocs.org/en/latest/usage/install.html): `# easy_install twython`

Para configurar web.py con servidor web consultar la [documentacion de web.py](http://webpy.org/cookbook/)

#Fichero de Configuracion `boe.conf`
* [db]
 * host = IP del servidor MongoDB
 * puerto = Puerto del servidor MongoDB
 * nombre = Nombre de la Base de Datos
 *  #usuario= (OPCIONAL)Usuario si es necesario identificarse contra el servidor
 *  #clave= (OPCIONAL)Clave si es necesario identificarse contra el servidor
* [log]
 * formato= En el [formato de logging python](http://docs.python.org/2/library/logging.html#logrecord-attributes) cambiando los % por $ 
 * nivel = Un valor entre 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
* [celery]
 * activo = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean) para activar Celery
 * simultaneos = Numero de procesos simultaneos para analizar los distintos BOEs
 * pool = Numero de conexiones maximas
 * meta = Valor para el parametro [taskmeta_collection](http://docs.celeryq.org/en/latest/configuration.html#celery-mongodb-backend-settings)
 * formato_log = Usado en la clave CELERYD\_LOG_FORMAT en el [formato de logging python](http://docs.python.org/2/library/logging.html#logrecord-attributes) cambiando los % por $
 * formato_log_tareas = Usado en la clave CELERYD\_TASK\_LOG\_FORMAT en el [formato de logging python](http://docs.python.org/2/library/logging.html#logrecord-attributes) cambiando los % por $
* [web]
 * debug = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean) Con este valor a Verdadero la session tiene problemas
 * autoregistro = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean) permite hacer registros automaticos al insertar un correo nuevo.
 * tema = Path donde se encuentra las plantillas de la web
 * multilogin = Permite hacer login con distintos usuarios, puede dar problemas con "debug" verdadero. Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean)
 * cookie_name = Nombre de la Cookie
 * cookie_domain = Dominio de la Cookie
 * cookie_salt = Salt para la Cookie __Es recomendable modificarla__
 * cookie_dir = Path donde se encuentran almacenadas las cookies
* [conexion]
 * #proxy= (OPCIONAL) Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean)
permite usar como salida a intenet el proxy configurado en el equipo, util si se quiere usar en universidades, ...
* #[twitter]\(OPCIONAL)
 * consumer_key = Clave Twitter
 * consumer_secret = Clave secreta de Twitter
* #[email]\(OPCIONAL)
 * email = Email de envio del correo
 * server = Host del servidor de corre
 * port = Puerto del servidor de correo
 * ssl = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean) para activar SSL
 * tls = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean) para activar TLS
 * #usuario = (OPCIONAL)Usuario si es necesario identificarse contra el servidor 
 * #clave = (OPCIONAL)Clave si es necesario identificarse contra el servidor
 
# Dependencias:
* __[pymongo](http://api.mongodb.org/python/current/ "PyMongo"):__ Como conector con la base de datos [MongoDB](http://www.mongodb.org/).
* __[WebPy](https://github.com/webpy/webpy "Framework WebPy"):__ Simple web Framework para Python.
* __[Celery](http://www.celeryproject.org "Celery"):__ Sistema de procesado multiple y distribuido.
* __[Twython](https://github.com/ryanmcgrath/twython "Twitter Python Lib"):__ Para el sistema de Login y DM en Twitter.

# WebUI Powered by:
* [Bootstrap](http://getbootstrap.com/getting-started/)
* [jQuery](http://jquery.com/download/)
* [DataTables](http://datatables.net/download/)
* [Mnemo Filetype Icons](http://www.iconarchive.com/show/mnemo-icons-by-hechiceroo.html)

#Puesta a punto
Antes de insertar reglas en el sistema es recomendame nutrilo con los datos como:
"seccion","departamento","epigrafe", ... que nos permitiran generar alertas genericas sobre apartados contretos,
cuanto mayor sea el numero de BOEs procesados mayor numero de opciones, si aparecen nuevas se van insertando con cada analisis.
<pre>
$ python boe_parser.py 2013/01/01 --fin 2013/11/11
$ celeryd
$ python pagina.py
</pre>
Se recomienda insertar en el crontab `01 8 * * 0-6 python -B ~/BOE_Alert/scan.py`<br/>
Si se tiene Celery esta activo, debes ejecutar `celery worker` o `celeryd`. Para que se procesen los distintos BOEs en paralelo.<br/>
Y acceder a 127.0.0.1:8080 para ver el portal de administracion.<br/>
Por ultimo es recomendable configurar un cron para que automatize todos los dias el analisis del BOE nuevo.

#Sobre las Reglas
Las opciones Titulo y Texto se usan como expresiones regulares para buscar una concordancia.
La opcion _'malfomado'_ es OPCIONAL y aparece en los BOEs del tipo A y B e implica que se ha detectado una imagen o contenido no precesable en modo texto.
Aun que no marques esta opcion, los BOEs malformados se veran en tus alertas, ya que solo sirve para eliminar posibles alertas no requeridas.

# Ejemplos
Procesa el dia de hoy
`$ python boe_parser.py`

Procesa desde el 2013 hasta hoy
`$ python boe_parser.py 2013/01/01`

Procesa todo el 2012
`$ python boe_parser.py 2012/01/01 --fin 2013/01/01`

Procesa todo el 2012 solo si hay reglas, util si solo se tiene reglas de un tipo, __NO recomendado__
`$ python boe_parser.py 2012/01/01 --fin 2013/01/01 --rapido`

Procesa todo el BOE con identificador BOE-S-2013-1
`$ python boe_parser.py --boe BOE-S-2013-1`

# TODO
* Normalizar nombre
* Gestor de trabajo para integracion con cloud API
* Mejora de Pagina Acerca
* Insertar apartados para cumplir "Ley de Cookies"
* Mejorar documentacion sobre configuracion de Reglas
* Hacer uso de Celery para la busqueda de expresiones regulares
* Mejorar el Sistema deteccion de reglas
* Poder cancelar la validacion de un nuevo eMail
* Envio de DM por Twitter
* Mejorar cifrado de algunos datos
