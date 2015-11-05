---
layout: post
title:  "Log de entrevista: Google"
date:   2015-10-10
categories: programacion
tags: java python algoritmos
---
Lo de abajo son las preguntas de entrevistas que me preguntaron en la ronda de entrevista por tel&eacute;fono 
con Google. Lo escrib&iacute; hace par de meses para apoyar a mi mejor amiga que estaba aplicando para ser
ing. de software tambi&eacute;n. Bueno dejo de hablar huevadas y aquí son la primera pregunta técnica, espero 
que a alguien le sirve.

###Primera pregunta
Dado un arreglo de numeros de un digito, digamos [1,2,5,9], que representa el número 1259. Retorna un arreglo de numeros de un dígito de la misma forma, representando el número + 1. Es decir, si me da [1,2,5,9] debo retornar [1,2,6,0].

Lo cagado del problema presenta cuando el último dígito es 9, ya que hay que sumar 1 al dígito anterior también; y si ese tambien es 9, hay que hacer lo mismo para el dígito anterior. Y en el peor caso, si te da [9,9,9,9] debes retornar [1,0,0,0,0] necesitas aumentar el tamano del arreglo también. Eso es lo jodido. 

Le pregunte si podia usar python, y me acepto. Luego escribi algo asi:

{% highlight python%}
def increment_one(num_array):
    if not num_array:
        return [1]
    last_digit = num_array[-1]
    if last_digit < 9:
        num_array[-1] += 1
        return num_array
    return increment_one(num_array[:-1]) + [0]
{% endhighlight %}

(Nota: después que ya me dio la entrevista onsite, me di cuenta que hice una CAGADA aqui. 
Quizas uds ya se dieron cuenta, pero de todos modos los verán  al final)

###Segunda pregunta:
Dado el interface Iterator de Java:
{% highlight java %}
interface Iterator {
  bool hasNext();
  Object next();
}
{% endhighlight %}

bool hasNext() que te diga si hay siguiente elemento, y Object next() que retorna el siguiente elemento y avanza el iterator por uno; implemente una clase de Iterator que aparte de esos 2 metodos, tenga un tercer metodo Object peek(), que retorna el elemento sin avanzar el iterator. La clase nueva acepta un Iterator en el constructor.

Es decir algo asi:
{% highlight java %}
class PeekIterator implements Iterator {
    PeekIterator(Iterator i) {} 
    bool hasNext() {}
    Object next() {}
    Object peek() {} 
} 
{% endhighlight %}

Pensado un rato, para poder saber cual es el siguiente elemento cuando llama peek(), tenemos que llamar next() del iterator pasado. Y para no avanzar el iterator, hay que recordar ese valor de alguna forma para usarlo de nuevo cuando peek o next sea llamado. Entonces primero hay que declarar un Object para guardar esa referencia:

{% highlight java %}
class PeekIterator implements Iterator {
    Iterator source;
    Object temp;
    PeekIterator(Iterator i) {
        source = i;
    } 
    bool hasNext() {
        if (temp != null) {
            return true; 
        } 
        return source.hasNext();
    }
    Object next() {
        if (temp != null) {
            Object return = temp;
            temp = null;
            return temp;
        }
        return source.next();
    }
    Object peek() {
        if (temp == null) {
            temp = source.next();
        }
        return temp;
    } 
} 
{% endhighlight %}

Entonces, si llama peek, veremos el siguiente elemento usando next, pero acordamos ese valor. Para la siguiente llamada de peek o next, retornamos ese valor. Si llama a next, hay que descartar el valor de peek ya que el iterator avanzo. 

Todo esta bonito. 

Luego el entrevistador me recordo que source.next() puede retornar null, en el caso si metes un null a una List 
por ejemplo. Entonces cambie al codigo para use un boolean para acordar si temp tiene un valor valido o no. (De ley 
me quit&oacute; puntos aqu&iacute;).



###La tercera pregunta:

Dado una cadena con caracteres ‘1’, ‘0’ y ‘?’. Digamos ‘1001?1?00?’ imprima todas las combinaciones reemplazando ? por 1 o 0.

Es decir, si hay 3 ?’s, tendre que hacer 8 combinaciones replazando ? por 1 o 0.
Esto se puede hacer con recursiones facilmente. Pero la forma que pense es: es como si genero numeros binarios de 0 hasta 11111 (numeros de 1 es iguales a numeros de ?), y luego replazo cada ? por el numero de digitos correspondiente.

Podia generar esos numeros usando un entero luego convirtiendo en una cadena en representacion binario, pero ese entonces me dio pereza ya que si los numeros esta representados como un arreglo de digitos es mas facil. Y puedo reusar la respuesta del pregunta 1; cambiando numero decimal a numeros binarios.

{% highlight python %}
def increment_one(num_array):
    if not num_array:
        return [1]
    last_digit = num_array[-1]
    if last_digit < 1:
        num_array[-1] += 1
        return num_array
    return increment_one(num_array[:-1]) + [0]
{%endhighlight%}


teniendo esta funcion, el resto es sencillo:

{% highlight python %}
def printallcombination(format):
    num_interrogation = count(filter(lambda s: s=='?'), format)
    start = [0] * num_interrogation
    print_format = format.replace('?', '%d')
    while True:
        print print_format % start
        start = increment_one(start)
        if len(start) > num_interrogation:
            break
{%endhighlight%}

(Y parece que le gust&oacute; que he reusado el c&oacute;digo anterior. :))

(la cagada de la primera pregunta es que num_array[:-1] crea una arreglo nuevo con elementos del viejo, y es tiempo lineal con respecto al tamaño del arreglo. Entonces el tiempo de ejecución termina siendo cuadrática en el peor caso, que es bien barbacha…)
