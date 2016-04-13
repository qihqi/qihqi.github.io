---
layout: post
title:  "Dependency Injection in Bottle/Flask (Python)"
date:   2016-04-02
tags: python xml ats
categories: python
---

Primer on Dependency Injection
------------------------------

In a system constructed in a object oriented fashion, we usually
have two types of objects: _Data objects_, where
stores the data and _Service objects_, which manipulates the data. For example,
if it is a database backed application it usually has some
object that talks to the database, which is the Service object.

Say, we have 3 service objects
{% highlight python%}
class ServiceA(object):
    def do_work():
        pass

class ServiceB(object):
    def do_work():
        pass

class ServiceC(object):
    def do_work():
        pass
{% endhighlight %}

Now say, that ServiceB need to use ServiceA, it need to get to ServiceA somehow.
One of the antipatterns people used to use is to make ServiceA a singleton,
then you have something like this:

{% highlight python%}
class ServiceA(object):
    def do_work():
        pass

    @classmethod
    def get_instance(cls):
        # blah blah

class ServiceB(object):
    def do_work():
        ServiceA.get_instance().do_work()

class ServiceC(object):
    def do_work():
        pass
{% endhighlight %}

_Dependency Injection_ basically says, _don't do that shit!!_ Using singleton
making testing of ServiceB a pain, and makes it impossible to let ServiceB
work with another service similar to A. If ServiceB needs ServiceA, it should
ask it in the constructor, like this:
{% highlight python%}
class ServiceA(object):
    def do_work(self):
        pass

    @classmethod
    def get_instance(cls):
        # blah blah

class ServiceB(object):
    def __init__(self, service_a):
        self.service_a = service_a

    def do_work(self):
        self.service_a.do_work()

class ServiceC(object):
    def do_work(self):
        pass
{% endhighlight %}

[This (pretty long) Google talk explains this idea very well](https://www.youtube.com/watch?v=-FRm3VPhseI).

Sometimes the term *Dependency Injection* is sometimes refers a dependency injection
framework, like Spring and Guice for Java, all that those framework does it to
save you from typing out the constructors of the services. Here we will only talk
it as the idea of asking dependencies explicitly, usually in constructors.

Dependency injection in web frameworks
--------------------------------------

Usually we instantiate service objects in the program's entry point,
like the main function. However, most web frameworks there is no such
entry point.

Here is a extremely simple wsgi app written with bottle.


{% highlight python%}
import bottle
app = Bottle()
@app.get('/')
def index():
    return 'hello world'

if __name__ == '__main__':
    bottle.run(app)
{% endhighlight %}

Now, index needs to use ServiceA, ServiceB, and ServiceC. Where do you put them?
Usual approaches are using globals, annotations or closures.

As globals
----------
{% highlight python%}
import bottle
app = Bottle()

a = ServiceA()
b = ServiceB(service_a=a)
c = ServiceC(b, a)

@app.get('/')
def index():
    # do stuff with a,b,c
    return 'hello world'

if __name__ == '__main__':
    bottle.run(app)
{% endhighlight %}

Note that here a, b, c are effectively singletons, but that does not
violate principles of dependency injection because inside of ServiceB does not
read ServiceA from the global, but from its member variable. That makes
us free to pass in a different object for ServiceA when needed.

The advantage of thise approach is the simplicity. We can also move all the
instantiation to a config.py file and every other files just import
the services it needs.
However, now index is really hard to test. We cannot test it independently of
ServiceA, ServiceB and ServiceC, and cannot mock those services out without
monkey patching. We can sort of mitigate that by move most of the functionality
inside some service and let the url handler just forward the call, and leave
those handlers untested.

Decorators
----------
{% highlight python%}
import bottle
app = Bottle()

a = ServiceA()
b = ServiceB(service_a=a)
c = ServiceC(b, a)

@app.get('/')
@uses_service(a,b,c)
def index(a, b, c):
    # do stuff with a,b,c
    return 'hello world'

if __name__ == '__main__':
    bottle.run(app)
{% endhighlight %}

We can write a custom decorator to pass the dependent service as parameters to 
the needed function.
This makes it look little nicer, and gives the impression that index function is not reading
globals anymore. However, we cannot directly call index with custom a, b and
c as the decorator call replaces the old function with a wrapped one. So it's really
the same.

Of course we can test the unwrapped version by not using decorator syntax,
like this
{% highlight python %}
def index(a, b, c):
    # do stuff with a,b,c
    return 'hello world'
app.get('/')(uses_service(a,b,c)(index))
{% endhighlight %}

but this is plain ugly. Also, doing this for every url handler could be a pain!

Using closures
--------------
{% highlight python%}
import bottle

def make_wgsi_app(a, b ,c)
  app = Bottle()

  @app.get('/')
  @uses_service(a,b,c)
  def index(a, b, c):
      # do stuff with a,b,c
      return 'hello world'
  return app

if __name__ == '__main__':
    a = ServiceA()
    b = ServiceB(service_a=a)
    c = ServiceC(b, a)
    bottle.run(make_wgsi_app(a, b, c))

{% endhighlight %}

This is my favorite. It effectively put the service instantiation in the point
of entry, and allows testing the wgsi app passing mocked out versions of
service a b or c. Though, because make_wsgi_app returns a wsgi app instead of
a function object, we need to test index through it, webtest package is a
great tool to accomplish that.

Using this method, you can pass dependencies to a group of url handlers
with similar dependencies as well.
