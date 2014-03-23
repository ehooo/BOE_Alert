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
Sistema de procesado y alertar para el BOE (Boletin Oficial del Estado).

# Instalar
* [python](http://www.python.org/download/): `# apt-get install python`
* [easy\_install](https://pypi.python.org/pypi/setuptools): `# apt-get install python-pip`
* [django](https://www.djangoproject.com): `# pip install Django==1.6.1`
* [Python Social Auth](https://github.com/omab/python-social-auth): `# pip install python-social-auth`
* [Celery](http://www.celeryproject.org/install/): `# easy_install Celery`
* [Twython](https://twython.readthedocs.org/en/latest/usage/install.html): `# pip install twython`


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
$ python manager.py boe_start 2013/01/01
$ python manager.py celeryd
$ python manager.py runserver
</pre>

#Sobre las Reglas
Las opciones Titulo y Texto se usan como expresiones regulares para buscar una concordancia.
La opcion _'malfomado'_ es OPCIONAL y aparece en los BOEs del tipo A y B e implica que se ha detectado una imagen o contenido no precesable en modo texto.
Aun que no marques esta opcion, los BOEs malformados se veran en tus alertas, ya que solo sirve para eliminar posibles alertas no requeridas.


# TODO
* Hacer `$ python manager.py boe_start 2013/01/01`
* Mejora de Pagina Acerca
* Insertar apartados para cumplir "Ley de Cookies"
* Mejorar documentacion sobre configuracion de Reglas
* Hacer uso de Celery para la busqueda de expresiones regulares
* Mejorar el Sistema deteccion de reglas
* Poder cancelar la validacion de un nuevo eMail
* Envio de DM por Twitter
* Mejorar cifrado de algunos datos