# Copyright

"""Define the `@callback` decorator.

See :pep:`318` for an introduction to decorators.
"""

from .caller import caller_name


def is_iterable(x):
    """Return `True` if `x` is iterable.

    Examples
    --------
    >>> is_iterable('abc')
    True
    >>> is_iterable((1,2,3))
    True
    >>> is_iterable(5)
    False
    >>> def c():
    ...     for i in range(5):
    ...         yield i
    >>> is_iterable(c())
    True
    """
    try:
        iter(x)
        return True
    except TypeError:
        return False

def callback(method):
    """Enable callbacks on `method`.

    This decorator should make it easy to setup callbacks in a rich
    GUI.  You only need to decorate potential hooks, and maintain a
    single dict with all the callbacks for the class.  This beats
    passing each of the callbacks into the class' `__init__` function
    individually.

    Examples
    --------

    Callbacks are called with the class instance, method instance, and
    returned arguments of the method they're attached to.

    >>> def c(self, method, *args):
    ...     print '\\n  '.join([
    ...             'callback:',
    ...             'class:    %s' % self,
    ...             'method:   %s' % method,
    ...             'returned: %s' % args])

    For some class, decorate any functions you're interested in
    attaching callbacks too.  Also, add a `_callbacks` attribute
    holding the callbacks, keyed by function name.

    >>> class X (object):
    ...     def __init__(self):
    ...         self._callbacks = {'xyz': c}
    ...
    ...     @callback
    ...     def xyz(self):
    ...         "xyz's docstring"
    ...         print 'usual xyz business'
    ...         return (0, 1, 1, 2, 3, 5)
    ...
    ...     @callback
    ...     def abc(self):
    ...         "abc's docstring"
    ...         print 'usual abc business'
    ...
    >>> x = X()

    Here's our callback on `xyz`.

    >>> r = x.xyz()  # doctest: +ELLIPSIS
    usual xyz business
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.xyz of <hooke.util.callback.X object at 0x...>>
      returned: (0, 1, 1, 2, 3, 5)
    >>> r
    (0, 1, 1, 2, 3, 5)

    The decorated method preserves the original docstring.

    >>> print x.xyz.__doc__
    xyz's docstring

    So far, we haven't attached a callback to `abc`.

    >>> r = x.abc()
    usual abc business

    Now we attach the callback to `abc`.

    >>> x._callbacks['abc'] = c
    >>> r = x.abc()  # doctest: +ELLIPSIS
    usual abc business
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.abc of <hooke.util.callback.X object at 0x...>>
      returned: None

    You can also place an iterable in the `_callbacks` dict to run an
    array of callbacks in series.

    >>> def d(self, method, *args):
    ...     print 'callback d'
    >>> x._callbacks['abc'] = [d, c, d]
    >>> r = x.abc()  # doctest: +ELLIPSIS
    usual abc business
    callback d
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.abc of <hooke.util.callback.X object at 0x...>>
      returned: None
    callback d
    """
    def new_m(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        callback = self._callbacks.get(method.func_name, None)
        nm = getattr(self, method.func_name)
        if is_iterable(callback):
            for cb in callback:
                cb(self, nm, result)
        elif callback != None:
            callback(self, nm, result)
        return result
    new_m.func_name = method.func_name
    new_m.func_doc = method.func_doc
    new_m.original_method = method
    return new_m

def in_callback(self, *args, **kwargs):
    """Enable callbacks inside methods.

    Sometimes :func:`callback` isn't granular enough.  This function
    can accomplish the same thing from inside your method, giving you
    control over the arguments passed and the time at which the call
    is made.  It draws from the same `._callbacks` dictionary.

    Examples
    --------

    Callbacks are called with the class instance, method instance, and
    returned arguments of the method they're attached to.

    >>> def c(self, method, *args, **kwargs):
    ...     print '\\n  '.join([
    ...             'callback:',
    ...             'class:    %s' % self,
    ...             'method:   %s' % method,
    ...             'args:     %s' % (args,),
    ...             'kwargs:   %s' % kwargs])

    Now place `in_callback` calls inside any interesting methods.

    >>> class X (object):
    ...     def __init__(self):
    ...         self._callbacks = {'xyz': c}
    ...
    ...     def xyz(self):
    ...         "xyz's docstring"
    ...         print 'usual xyz business'
    ...         in_callback(self, 5, my_kw=17)
    ...         return (0, 1, 1, 2, 3, 5)
    ...
    ...     def abc(self):
    ...         "abc's docstring"
    ...         in_callback(self, p1=3.14, p2=159)
    ...         print 'usual abc business'
    ...
    >>> x = X()

    Here's our callback in `xyz`.

    >>> r = x.xyz()  # doctest: +ELLIPSIS
    usual xyz business
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.xyz of <hooke.util.callback.X object at 0x...>>
      args:     (5,)
      kwargs:   {'my_kw': 17}
    >>> r
    (0, 1, 1, 2, 3, 5)

    Note that we haven't attached a callback to `abc`.

    >>> r = x.abc()
    usual abc business

    Now we attach the callback to `abc`.

    >>> x._callbacks['abc'] = c
    >>> r = x.abc()  # doctest: +ELLIPSIS
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.abc of <hooke.util.callback.X object at 0x...>>
      args:     ()
      kwargs:   {'p2': 159, 'p1': 3.1400000000000001}
    usual abc business

    You can also place an iterable in the `_callbacks` dict to run an
    array of callbacks in series.

    >>> def d(self, method, *args, **kwargs):
    ...     print 'callback d'
    >>> x._callbacks['abc'] = [d, c, d]
    >>> r = x.abc()  # doctest: +ELLIPSIS
    callback d
    callback:
      class:    <hooke.util.callback.X object at 0x...>
      method:   <bound method X.abc of <hooke.util.callback.X object at 0x...>>
      args:     ()
      kwargs:   {'p2': 159, 'p1': 3.14...}
    callback d
    usual abc business
    """
    method_name = caller_name(depth=2)
    callback = self._callbacks.get(method_name, None)
    nm = getattr(self, method_name)
    if is_iterable(callback):
        for cb in callback:
            cb(self, nm, *args, **kwargs)
    elif callback != None:
        callback(self, nm, *args, **kwargs)
