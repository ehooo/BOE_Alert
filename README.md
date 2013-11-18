# Licencia
Copyright (C) 2013  ehooo

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
* boe_parser.py: Que procesa el BOE de un dia dado, o el ultimo publicado.

# Dependencias:
* __[pymongo](http://api.mongodb.org/python/current/ "PyMongo"):__ Como conector con la base de datos [MongoDB](http://www.mongodb.org/).
* __[WebPy](https://github.com/webpy/webpy "Framework WebPy"):__ Simple web Framework para Python.
* __[Celery](https://github.com/webpy/webpy "Framework WebPy"):__ Sistema de procesado multiple y distribuido.

# Powered by:
* [Bootstrap](http://getbootstrap.com/getting-started/)
* [jQuery](http://jquery.com/download/)
* [DataTables](http://datatables.net/download/)

# Instalar
* [python](http://www.python.org/download/): `# apt-get install python`
 * [easy\_install](https://pypi.python.org/pypi/setuptools): `# apt-get install python-pip`
* [mongoDB](http://www.mongodb.org/downloads): `# apt-get install mongodb-server`
* [pymongo](http://api.mongodb.org/python/current/installation.html): `# apt-get install python-pymongo` o `# easy_install pymongo`
* [web.py](http://webpy.org/install): `# easy_install web.py`
* [Celery](http://www.celeryproject.org/install/): `# easy_install Celery`

Para configurar web.py con servidor web consultar la [documentacion de web.py](http://webpy.org/cookbook/)

#Fichero de Configuracion
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
 * simultaneos = Numero de procesos simultaneos para analizar los distintos BOEs
 * formato_log = Usado en la clave CELERYD\_LOG_FORMAT en el [formato de logging python](http://docs.python.org/2/library/logging.html#logrecord-attributes) cambiando los % por $
 * formato_log_tareas = Usado en la clave CELERYD\_TASK\_LOG\_FORMAT en el [formato de logging python](http://docs.python.org/2/library/logging.html#logrecord-attributes) cambiando los % por $
* [web]
 * debug = Un valor Verdadero o Falso para [ConfigParser](http://docs.python.org/2/library/#ConfigParser.RawConfigParser.getboolean)
 * tema = Path donde se encuentra las plantillas de la web

# TODO
* Paguina Acerca
* Hacer uso de Celery para la busqueda de expresiones regulares
* Mejorar el Sistema deteccion de reglas
* Mejorar el Sistema de envio de alertas
* Sistema login
* Sistema multiusuario

# Ejemplos
Procesa el dia de hoy
`$ python boe_parser.py`

Procesa desde el 2013 hasta hoy
`$ python boe_parser.py 2013/01/01`

Procesa todo el 2012
`$ python boe_parser.py 2012/01/01 --fin 2013/01/01`

#Puesta a punto
Antes de insertar reglas en el sistema es recomendame nutrilo con los datos como:
"seccion","departamento","epigrafe","origen\_legislativo","materia","alerta"
que nos permitiran generar alertas genericas sobre apartados contretos, cuanto mayor sea el numero de
BOEs procesados mayor numero de opciones, si aparecen nuevas se van insertando con cada analisis.
<pre>
$ python boe_parser.py 2013/01/01 --fin 2013/11/11

$ python pagina.py
</pre>
Y acceder a 127.0.0.1:8080/reglas para ver el portal de administracion.<br/>
Por ultimo es recomendable configurar un cron para que automatize todos los dias el analisis del BOE nuevo.

#Sobre las Reglas
Las opciones Titulo y Texto se usan como expresiones regulares para buscar una concordancia.
La opcion _'malfomado'_ es OPCIONAL y aparece en los BOEs del tipo A y B e implica que se ha detectado una imagen o contenido no precesable en modo texto.
Aun que no marques esta opcion, los BOEs malformados se veran en tus alertas, ya que solo sirve para eliminar posibles alertas no requeridas.
