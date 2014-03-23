var $=jQuery;

var ES_LANG = {
	"oPaginate":{
		"sFirst": "primero",
		"sLast": "ultimo",
		"sNext": "siguiente",
		"sPrevious": "anterior"
	},
	"sEmptyTable": "No existen reglas",
	"sInfo": "Reglas de _START_ a _END_ de un total de _TOTAL_",
	"sInfoEmpty": "No existen reglas",
	"sInfoFiltered": " - sin filtrar _MAX_",
	"sInfoPostFix": "",
	"sInfoThousands": "",
	"sLengthMenu": "Mostrar _MENU_ reglas",
	"sLoadingRecords": "Cargando datos del servidor",
	"sProcessing": "Cargando datos del servidor",
	"sSearch": "buscar:",
	"sUrl":"",
	"sZeroRecords": "No existen reglas"
}

$(document).ready(function() {
	if(!window.location.search ||
			( window.location.search.indexOf('login')==-1 &&
			window.location.search.indexOf('oauth_token')==-1 )
		){
		check_alertas();
	}
	$(".no_implementado input").attr("disabled","disabled");
	pagina_alertas();
	pagina_reglas();
});

function check_alertas(){
	jQuery.ajax({
		cache:false,
		type: 'POST',
		url: "/alertas",
		dataType: 'json',
		data: {'total':true},
		error: maneja_error,
		success:function(data){ $('#total_alertas').text(data.total); }
	});
};

function maneja_error(jqXHR, textStatus, errorThrow){
	var error = jQuery.parseJSON(jqXHR.responseText).error;
	if(error)
		alert(error);
	else
		alert(textStatus);
};
function pagina_alertas(){

	var alertas = $('#alertas_boe').dataTable( {
		"oLanguage": ES_LANG,
		"bProcessing": true,
		"bServerSide": true,
		"iDisplayLength": 10,
		"aLengthMenu": [ 10, 15, 20 ],
		"sDom":'l<"borrar_alerta glyphicon glyphicon-trash">frtip',
		"sServerMethod": "POST",
        "sAjaxSource": "/alertas",
		"oTableTools": { "sRowSelect": "single" },
		"fnDrawCallback":check_boton,
		"fnRowCallback": prepare_row
    } );

	var boton = $('<button/>',{
		'type':'button',
		'class':'btn btn-primary btn-xs',
		"data-toggle":"button",
		'disabled':'disabled'
	});
	$(".borrar_alerta").wrap(boton);

	$('#alertas_boe_wrapper .borrar_alerta').parent().click(function(){
		var post_data = new Array();
		jQuery.each($(this.parentNode).find('tr.row_selected'), function(i, element){
			post_data.push($(element).attr('id'));
		});
		post_data = {'borrar': post_data.join() };
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/alertas",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(){ alertas.fnDraw(); check_alertas(); }
		});
	});

	function check_boton(){
		var a = $('#alertas_boe_wrapper .borrar_alerta').parent();
		var b = $('#alertas_boe').find('tr.row_selected').length;
		if (b > 0){
			a.removeAttr('disabled');
		}else{
			a.attr('disabled','disabled');
		}
	};

	function prepare_row(nRow, aData, iDisplayIndex, iDisplayIndexFull){
		var boe = $('td:eq(0)', nRow);
		if (aData[1]){
			boe.append(
				$('<a/>',{'class':'pdf', 'title':'pdf', 'href':'http://boe.es/boe/dias/'+aData[1]+'/pdfs/'+aData[0]+'.pdf', 'target':'_blank'}).append(
					$('<img/>',{'src':'/static/images/pdf.png', 'alt':'pdf'})
				)
			);
		}
		boe.append(
			$('<a/>',{'class':'html', 'title':'html', 'href':'http://boe.es/diario_boe/txt.php?id='+aData[0] , 'target':'_blank'}).append(
				$('<img/>',{'src':'/static/images/txt.png', 'alt':'html'})
			)
		);
		boe.append(
			$('<a/>',{'class':'epub', 'title':'epub', 'href':'http://boe.es/diario_boe/epub.php?id='+aData[0] , 'target':'_blank'}).append(
				$('<img/>',{'src':'/static/images/epub.png', 'alt':'epub'})
			)
		);
		boe.append(
			$('<a/>',{'class':'xml', 'title':'xml', 'href':'http://boe.es/diario_boe/xml.php?id='+aData[0] , 'target':'_blank'}).append(
				$('<img/>',{'src':'/static/images/xml.png', 'alt':'xml'})
			)
		);
		//TODO Insertar enlaces a xml y epub
		$(nRow).attr('id',aData[0]);
		$(nRow).click( function( e ) {
			if ( $(this).hasClass('row_selected') ) {
				$(this).removeClass('row_selected');
			} else {
				$(this).addClass('row_selected');
			}
			check_boton();
		});
	};
};

function pagina_reglas(){
	var reglas_rapidas = $('#reglas_rapidas').dataTable( {
		"oLanguage": ES_LANG,
		"bProcessing": true,
		"bServerSide": true,
		"iDisplayLength": 10,
		"aLengthMenu": [ 10, 15, 20 ],
		"sDom":'l<"nueva_regla glyphicon glyphicon-plus"><"borrar_regla glyphicon glyphicon-trash">frtip',
		"sServerMethod": "POST",
        "sAjaxSource": "/reglas/rapidas",
		//"sCookiePrefix": "session_cookie",
		"oTableTools": { "sRowSelect": "single" },
		"fnDrawCallback":check_buttons,
		"fnRowCallback": prepare_row
    } );
	var boe_s = $('#boe_s').dataTable( {
		"oLanguage": ES_LANG,
		"bProcessing": true,
		"bServerSide": true,
		"iDisplayLength": 10,
		"aLengthMenu": [ 10, 15, 20 ],
		"sDom":'l<"nueva_regla glyphicon glyphicon-plus"><"borrar_regla glyphicon glyphicon-trash">frtip',
		"sServerMethod": "POST",
        "sAjaxSource": "/reglas/S",
		//"sCookiePrefix": "session_cookie",
		"oTableTools": { "sRowSelect": "single" },
		"fnDrawCallback":check_buttons,
		"fnRowCallback": prepare_row
    } );
	var boe_a = $('#boe_a').dataTable( {
		"oLanguage": ES_LANG,
		"bProcessing": true,
		"bServerSide": true,
		"iDisplayLength": 10,
		"aLengthMenu": [ 10, 15, 20 ],
		"sDom":'l<"nueva_regla glyphicon glyphicon-plus"><"borrar_regla glyphicon glyphicon-trash">frtip',
		"sServerMethod": "POST",
        "sAjaxSource": "/reglas/A",
		//"sCookiePrefix": "session_cookie",
		"oTableTools": { "sRowSelect": "single" },
		"fnDrawCallback":check_buttons,
		"fnRowCallback": prepare_row
    } );
	var boe_b = $('#boe_b').dataTable( {
		"oLanguage": ES_LANG,
		"bProcessing": true,
		"bServerSide": true,
		"iDisplayLength": 100,
		"aLengthMenu": [ 10, 150, 20 ],
		"sDom":'l<"nueva_regla glyphicon glyphicon-plus"><"borrar_regla glyphicon glyphicon-trash">frtip',
		"sServerMethod": "POST",
        "sAjaxSource": "/reglas/B",
		//"sCookiePrefix": "session_cookie",
		"oTableTools": { "sRowSelect": "single" },
		"fnDrawCallback":check_buttons,
		"fnRowCallback": prepare_row
    } );

	$('#guardar_reglas_rapidas').click(function(){
		var post_data = $("#form_reglas_rapidas").serialize();
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/rapidas",
			dataType: 'json',
			data: post_data,
			error:maneja_error,
			success:function(data, textStatus, jqXHR ){
				$('#from_reglas_rapidas [type="text"]').val('');
				$("#modal_reglas_rapidas").modal('hide');
				reglas_rapidas.fnDraw();
				boe_s.fnDraw();
				boe_a.fnDraw();
				boe_b.fnDraw();
			}
		});
	});
	$('#guardar_boe_s').click(function(){
		var post_data = $("#form_boe_s").serialize();
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/S",
			dataType: 'json',
			data: post_data,
			error:maneja_error,
			success:function(data, textStatus, jqXHR ){
				$('#from_boe_s [type="text"]').val('');
				$("#from_boe_s option:selected").removeAttr('selected');
				$("#from_boe_s input:checked").removeAttr('checked');
				$("#modal_boe_s").modal('hide');
				boe_s.fnDraw();
			}
		});
	});
	$('#guardar_boe_a').click(function(){
		var post_data = $("#form_boe_a").serialize();
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/A",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(data, textStatus, jqXHR ){
				$('#from_boe_a input[type="text"]').val('');
				$("#from_boe_a input:checked").removeAttr('checked');
				$("#from_boe_a option:selected").removeAttr('selected');
				$("#modal_boe_a").modal('hide');
				boe_a.fnDraw();
			}
		});
	});
	$('#guardar_boe_b').click(function(){
		var post_data = $("#form_boe_b").serialize();
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/B",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(data, textStatus, jqXHR ){
				$('#from_boe_b input[type="text"]').val('');
				$("#from_boe_b option:selected").removeAttr('selected');
				$("#from_boe_b input:checked").removeAttr('checked');
				$("#modal_boe_b").modal('hide');
				boe_b.fnDraw();
			}
		});
	});

	$('#alias_reglas_rapidas').keypress(function(eventObject){
		var a = $('#re_expre_reglas_rapidas');
		var t = a.val();
		if(eventObject.charCode == 0){
			if(eventObject.keyCode == 8)
				t = t.substr(0,t.length-1);
		}else
			t = t.concat( String.fromCharCode(eventObject.charCode) );
		a.val( t );
	});
	
	$('label[for="re_expre_reglas_rapidas"]').append(
		$('<a/>',{
			'class':"glyphicon glyphicon-question-sign",
			'href':'http://docs.python.org/2/howto/regex.html#regex-howto',
			'target':'_blank',
			'title':'Ayuda sobre Expresiones Regulares en python'
		})
	);
	var boton = $('<button/>',{
		'type':'button',
		'class':'btn btn-primary btn-xs',
		"data-toggle":"button"
	});
	$(".borrar_regla").wrap(boton);
	$(".nueva_regla").wrap(boton);
	$(".modal").on('show.bs.modal', function () { $(".nueva_regla").parent().removeClass('active'); });
	$(".modal").on('shown.bs.modal', function () { $(".nueva_regla").parent().removeClass('active'); });

	$('#reglas_rapidas_wrapper .nueva_regla').parent().click(function(){ $("#modal_reglas_rapidas").modal('show'); });
	$('#boe_s_wrapper .nueva_regla').parent().click(function(){ $("#modal_boe_s").modal('show'); });
	$('#boe_a_wrapper .nueva_regla').parent().click(function(){ $("#modal_boe_a").modal('show'); });
	$('#boe_b_wrapper .nueva_regla').parent().click(function(){ $("#modal_boe_b").modal('show'); });

	$('#reglas_rapidas_wrapper .borrar_regla').parent().click(function(){
		var post_data = $(this.parentNode).find('tr.row_selected');
		post_data = {'borrar':post_data.attr('id')};
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/rapidas",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(){
				reglas_rapidas.fnDraw();
				boe_s.fnDraw();
				boe_a.fnDraw();
				boe_b.fnDraw();
			}
		});
	});
	$('#boe_s_wrapper .borrar_regla').parent().click(function(){
		var post_data = $(this.parentNode).find('tr.row_selected');
		post_data = {'borrar':post_data.attr('id')};
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/S",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(){ boe_s.fnDraw(); }
		});
	});
	$('#boe_a_wrapper .borrar_regla').parent().click(function(){ 
		var post_data = $(this.parentNode).find('tr.row_selected');
		post_data = {'borrar':post_data.attr('id')};
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/A",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(){ boe_a.fnDraw(); }
		});
	});
	$('#boe_b_wrapper .borrar_regla').parent().click(function(){ 
		var post_data = $(this.parentNode).find('tr.row_selected');
		post_data = {'borrar':post_data.attr('id')};
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas/B",
			dataType: 'json',
			data: post_data,
			error: maneja_error,
			success:function(){ boe_b.fnDraw(); }
		});
	});

	jQuery.each($('.modal-body select[name]'), function(index, element){
		var tipo = $(element).attr('name');
		var self = this;
		jQuery.ajax({
			cache:false,
			type: 'POST',
			url: "/reglas",
			dataType: 'json',
			data: {'listado':tipo},
			error: maneja_error,
			success:function(data, textStatus, jqXHR){
				$(self).empty();
				$(self).append($('<option/>',{'value':''}));
				jQuery.each(data, function(pos, item){
					var b = $('<option/>',{'value':item,'text':item});
					$(self).append(b);
				});
			}
		});
	});

	function prepare_row(nRow, aData, iDisplayIndex, iDisplayIndexFull){
		$(nRow).attr('id', aData.pop());
		jQuery.each(aData, function(index, element){
			var a = $('td:eq('+index+')', nRow);
			if(element === true){
				a.html($('<span/>',{'class':'glyphicon glyphicon-eye-open'}));
			}else if(element === false){
				a.html($('<span/>',{'class':'glyphicon glyphicon-eye-close'}));
			}
		});
		$(nRow).click( function( e ) {
			if ( $(this).hasClass('row_selected') ) {
				$(this).removeClass('row_selected');
			} else {
				$(this.parentNode).children('tr.row_selected').removeClass('row_selected');
				$(this).addClass('row_selected');
			}
			check_buttons(e.currentTarget);
		});
	};
	function check_buttons(element){
		var table = this;
		if (!(this instanceof Window))
			element = this;
		else
			table = $(element).parent();
		var a = $(element).parentsUntil('.panel-body').find('.borrar_regla').parent();
		var b = $(table).find('tr.row_selected').length;
		if (b > 0){
			a.removeAttr('disabled');
		}else{
			a.attr('disabled','disabled');
		}
	}
};


