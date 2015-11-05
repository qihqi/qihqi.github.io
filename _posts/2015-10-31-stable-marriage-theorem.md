---
layout: post
title:  "Teorema de Matrimonio Estable, y un aspecto machista de la sociedad"
date:   2015-10-31
tags: matematica combinatoria grafo apareamiento
categories: matematicas
---

Hace mucho mucho tiempo, en un lugar muy muy lejano, habia un pueblo aislado de los otros pueblos.
El pueblo hay  \\( n \\)  hombres y \\( n \\) mujeres solteros en edad de casarse. Y el matrimonio es 
algo muy importante para la estabilidad de la sociedad del pueblo, la gente
pregunta, &iquest; hay como casarse a los chicos, para que sea un <i>matrimonio estable</i>, es decir, 
que no haya el caso de que un marido de una, y una mujer de otro, prefieren escapar y estar juntos?


Formalmente, asumimos que cada hombre tiene una lista secreta que orden&oacute; 
a las mujeres en orden de su perferencia, y asi
mismos, cada mujer orden&oacute a los hombres en su perferencia. El orden de cada persona puede ser 
distinta, ya que cada persona tiene su individualidad, como en la vida real. Y asumimos que todos 
terminan casados al final (no tanto como la vida real, ouch). Lo que la gente no quiere que pase, es que 
haya 2 parejas, digamos  (Goku, Chi-Chi)  y  (Vegeta, Bulma)  donde  Goku  prefiere a  Bulma 
mas que su esposa  Chi-Chi  y   Bulma  prefiere a Goku mas que su esposo  Vegeta .

La buena noticia es que, en 1962, dos matem&aacute;ticos demostraron que, dado que el n&uacute;mero de hombres
y mujeres son iguales, siempre hay como hacer que todos los matrimonios estable. Y de hecho, ellos formularon 
un algoritmo de aparear a la gente, para llegar a una formulaci&oacute;n estable.

Y el algorithmo es va m&aacute;s o menos as&iacute;: 

1. todos los hombres va y declara a la mas preferida de su lista, en orden.
2. Si su preferida es soltera, lo acepta y ellos se amarra.
3. Si su preferida no es soltera, y ella prefiere a su pelado actual, 
  (o, su pelado actual esta mas arriba en la lista), no lo para bola.
4. O sino, si ella prefiere mas el nuevo, entonces corta con su pelado actual y amarra con el nuevo.
5. y el rechazado regrese y mira la siguiente de su lista y sigue.

El chiste es que ese proceso eventualmente termina, y todos estan amarrados con alguien. De ahi despues
de un a&ntilde;o o dos de noviazgo terminan casando, y ah&iacute; tienen tus matrimonios estables.

Y porque carajo eso funca? Bueno la intuicion es lo siguiente: primero se nota que, aunque los hombres
amarra y despues puede ser abandonados, las mujeres nunca vuelve soltera una vez amarrada. Es decir 
el numero de solteras disnumiye estrictamente. Entonces el proceso tiene que terminar.
Cuando el proceso termina, si hubiera 2 parejas, digamos  (Goku, Chi-Chi)  y  (Vegeta, Bulma) ,
entonces, como  Goku  prefiere a  Bulma , entonces significa que Goku declar&oacute; antes
que su esposa actual. Y como Bulma esta con otra persona Vegeta, significa que Bulma rechaz&oacute;
a Goku. Entonces no puede preferir a Goku m&aacute;s que Vegeta. 

Bueno, una vez sabiendo como obtener estabilidad social del pueblo, otra pregunta que podemos hacer es, 
el proceso descrito conviene m&aacute;s a los hombres o a las mujeres?

Aparentemente a las mujeres mas, ya que ellas no tienen que tomar iniciativas, una vez amarrada nunca es 
rechazada, y si cambia de pelado es por uno mejor. Y los hombres hace todo, puede salir con corazones rotos
varias veces hasta encontrar la final. Pero el resultado no es asi.

Puede que el proceso conviene a las mujeres, pero el resultado conviene a los hombres. De hecho, el apareamiento 
obtenido de la forma descrito arriba es llamado uun apareamiento "optimo para hombres" (male-optimal), y su 
definici&oacute;n es: "los hombres termina con la mejor mujer que quiere estar con el, y las mujeres termina
con el peor hombre que ella puede aceptar" (Donde las definiciones de "mejor" y "peor" es basado en el escala 
de cada persona). Una forma de observar eso es ver el caso especial donde todos los hombres tienen gustos super 
distintos y sus mas preferidas son todas distintas. Este caso, el algoritmo termina en el primer paso, cada 
hombre declara su perferida y es aceptado, y ahi termina. Obteniendo el &oacute;ptimo para los hombres. 

Aparte de existir el apareamiento optimo para masculino, tambien hay uno que es optimo para mujeres. Y la formas de o
btenerlo es sincillamente, cambiando el papel de hombre y mujeres. Entre esos 2 apareamientos estables que es optimo 
para algunos hombres y mujeres pero no todos de un g&eacute;nero. No conozco algoritmos para obtenerlos aun.

En conclusion, la mat&eacute;matica demuestra que:

1. Si las mujeres quieren conseguir el mejor hombre que puede conseguir, tienen que ser activas en vez de pasivas.
2. Si estas casada, no tiene raz&oacute;n de estar celosa, ya que ya sabes que eres la m&aacutes preferida que
   le pare bola. En cambio, los hombres si deben estar cuidados.

Bueno, conclusiones anteriores estan asumiendo que la preferencia de uno nunca cambia, y que la poblacion inicial
nunca cambia, que no es siempre verdad.

Este teorema es el que siempre uso cuando para mostrar que la mate es ch&eacute;vere. 
Invito a todos que sepa ingles que vea este video en [youtube](https://www.youtube.com/watch?v=Qcv1IqHWAzg) 
Ella explica mejor que yo XD.
