---
layout: post
title:  "Una forma alterna de generar XML"
date:   2015-10-22
tags: python xml ats
categories: programacion python

---

ML;NL(TL;DR): Si has hecho p&aacute;ginas con plantillas de HTML, puedes usar lo mismo para XML.

Si quieres ingresar facturas emitidas al sistema de SRI, tiene 2 formas:
o tipeas esos datos manualmente usando el aplicacion Java que se baja 
en las pajinas de SRI, o generas archivos de algun formato que ellos puede 
entender e importar al aplicacion antemencionado.

Entre ellos, tuve un request de generar archivos XML compartible para declarar el 
"Anexo Transaccional Simplificado" (ATS). 

La ficha tecnica de ATS se encuentra [aqui](http://descargas.sri.gob.ec/download/anexos/ats/FICHA_TECNICA_ATS_NUEVO_AGOSTO2013_V1.doc)

Basicamente, se requiere un archivo en XML que se ve asi:

{% highlight xml%}
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<iva>
  <TipoIDInformante>R</TipoIDInformante>
  <IdInformante></IdInformante> <!-- RUC -->
  <razonSocial></razonSocial> <!-- nombre de la compania -->
  <totalVentas></totalVentas>
  <!-- mas campos emitidos -->
  <compras>
    <!-- una lista de compras -->
  </compras>
  <ventas>
    <!-- Aqui viene uno de estos por cada cliente -->
    <detalleVentas>
      <idCliente>123</idCliente>
      <valorRetIva>0.00</valorRetIva>
      <valorRetRenta>0.00</valorRetRenta>
      <!-- mas campos emitidos -->
    </detalleVentas>
  </ventas>
  <ventasEstablecimiento>
    <ventaEst>
      <codEstab>001</codEstab>
      <ventasEstab></ventasEstab>
    </ventaEst>
  </ventasEstablecimiento>

  <anulados>
    <!-- Aqui viene uno de estos por cada uno de facturas anulados -->
    <detalleAnulados>
      <tipoComprobante>01</tipoComprobante>
      <autorizacion>1111897538</autorizacion>
      <!-- mas campos emitidos -->
    </detalleAnulados>
  </anulados>
</iva>
{% endhighlight %}

Como ya he hecho un servicio REST que retorna JSON, asum&iacute; que retornar XML
en vez de JSON no es muy diferente. Que consistir&aacute;n pasos como:
1. generar objetos con datos de bases de dato
2. convertir objetos en un dictionario (dict).
3. Convertir dict en XML (previamente en JSON, que es sincillamente llamando a json.dumps).

Googlee "python generate xml", y llegu&eacute; a la biblioteca de [lxml](https://pymotw.com/2/xml/etree/ElementTree/create.html). Me di cuenta que tener diccionario no sirve para un carajo, y hay que generar XML desde principio.

Planee de escribir un base class que generara XML como lo hice para dict con 
[SerializableMixin aqui](https://github.com/qihqi/HenryFACTService/blob/new_schema/henry/base/serialization.py#L84), 
luego crear 4 clases, para ventasEstablecimiento, detalleVentas, detalleAnulados, e iva (que contiene a los demas).
Pero me puse vago por unos d&iacute;as...

Cuando volv&iacute; a ver el problema, y viendo las p&aacute;ginas web que estoy haciendo con HTML. Se me
peg&oacute; que HTML es XML, HTML es XML!! HTML es XML!!! (repite 3 veces para las cosas importantes). Y teniendo
ya a&ntilde;os escribiendo platillas que genera HTML, porque no uso lo mismo para XML!!.

Al final, escrib&iacute; un plantilla de jinja2 [**aqui**](https://github.com/qihqi/HenryFACTService/blob/new_schema/templates/accounting/ats.xml). Que es basicamente copia y pega del formato de arriba.

