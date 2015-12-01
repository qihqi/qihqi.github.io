---
layout: post
title:  "Como tipear f&oacute;rmulas ch&eacute;veres in cualquier compu, sin instalar nada"
date:   2015-11-29
categories: herramientas 
tags: matematicas, latex
---

<b>ML;NL(TL;DR) El truco es usar LaTex in HTML. (Sigue leyendo si no sabes de que hablo).</b>

Aqui les traigo un truco para escribir matem&aacute;ticas con formulas cheveres
como esto: 
\$\$ \sum_{n=0}^{\infty} \int_1^{10} \frac{x^2+1}{\sin x}dx \$\$
o esto:
\$\$ \frac{x_1 + x_2 + ... + x_n}{n} \geq \sqrt[n]{x_1x_2...x_n}\$\$

Los unicos que necesitas para poder hacer esto son

- Un navegador de web decente, i.e. Chrome o Firefox.
- Estar en internet.
- Un editor de texto.

Primer paso, abre tu editor de texto favorito. Ojo, no es Word, no es Word, Word no es un
editor de texto!! Si usas Word no funca! Si no tienes un editor de texto usas Notepad por momento
y cons&iacute;guete uno mas decente despu&eacute;s. (Recomiendo Atom o Sublime Text).

y copias los siguientes:
{% highlight html %}
<html>
<body>
Habla loco!!
</body>
</html>
{% endhighlight %}

Guardas en un archivo llamado hola.html, ahi el icono debe aparecer el icono de tu browser,
y cuando lo abres, abrir&aacute; en tu browser verias "Habla loco!!" ahi.. De hecho, cualquier cosa que
escribes dentro del &lt;body&gt;&lt;/body&gt;que no tenga <> para salir iguales, y ahi es donde escribiremos las f&oacute;rmulas.
Ojo si estas en Windows
puede ser que Notepad asume que estas guardando con extensi&oacute;n .txt y te guarda hola.html.txt en vez
de hola.html, si te hace eso no va a funcionar, tienes que guardar como .html.

Bueno, luego para poner f&oacute;rmulas, primero copias y pegas lo siguiente justamente arriba de \<body\>
{% highlight html %}
<head>
<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>
</head>
{% endhighlight %}

Esto permita que insertara comandos para tipear formulas llamado LaTex (no menciones condones please, ya no 
es chistoso despu&eacute;s de 10 mil veces). Los comandos de LaTex es super intuitivo, los principales son:
\frac{arriba}{abajo} hace una fracci&oacute;n, _ para poner subscripts, ^ para poner exponente, \sum para
el simbolo de sumas. Con esos ya pueden hacer f&oacute;rmulas m&aacute;s o menos complicados. Si necesitas m&aacute;s
s&iacute;mbolos, mire en la pagina de [Art of Problem Solving](https://www.artofproblemsolving.com/wiki/index.php/LaTeX:Symbols). Al final, tienes que poner tu formula entre simbolos \\(  \\) para f&oacute;rmulas dentro de una linea, o
\\[ \\] para formulas en una linea aparte
cada lado. Por ejemplo, esto:

{% highlight html %}
<html>
<head>
<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>
</head>
<body>
Aqui viene la formula tuca:
\(  \frac{x_1 + x_2 + ... + x_n}{n} \geq \sqrt[n]{x_1x_2...x_n} \)

Y aqui una mas tuca:
\[ \sum_{n=0}^{\infty} \int_1^{10} \frac{x^2+1}{\sin x}dx \]

</body>
</html>
{% endhighlight %}

produce esto cuando lo abres en el browser:

Aqui viene la formula tuca:
\\(  \frac{x_1 + x_2 + ... + x_n}{n} \geq \sqrt[n]{x_1x_2...x_n} \\)

Y aqui una mas tuca:
\\[ \sum_{n=0}^{\infty} \int_1^{10} \frac{x^2+1}{\sin x}dx \\]

Esto es, de hecho, la forma t&iacute;pica para meter f&oacute;rmulas en las p&aacute;ginas
de web, pero nada nos para para usarlo en el escritorio. Y despu&eacute;s si es que quieres
instalar LaTex ya en serio, pueden seguir las instruciones aqui: [https://www.artofproblemsolving.com/wiki/index.php?title=LaTeX:Downloads](https://www.artofproblemsolving.com/wiki/index.php?title=LaTeX:Downloads).

