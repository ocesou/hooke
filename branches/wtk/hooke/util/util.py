# Copyright


class Closing (object):
    """Add .__enter__() .__exit__() for `with` statements.

    See :pep:`343`.
    """
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, *exc_info):
        try:
            close_it = self.obj.close
        except AttributeError:
            pass
        else:
            close_it()
