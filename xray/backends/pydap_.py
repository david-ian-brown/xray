import numpy as np

from .. import Variable
from ..core.utils import FrozenOrderedDict, Frozen, NDArrayMixin
from ..core import indexing

from .common import AbstractDataStore, robust_getitem


class PydapArrayWrapper(NDArrayMixin):
    def __init__(self, array):
        self.array = array

    @property
    def dtype(self):
        t = self.array.type
        if t.size is None and t.typecode == 'S':
            # return object dtype because that's the only way in numpy to
            # represent variable length strings; it also prevents automatic
            # string concatenation via conventions.decode_cf_variable
            return np.dtype('O')
        else:
            return np.dtype(t.typecode + str(t.size))

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            key = (key,)
        for k in key:
            if not (isinstance(k, (int, np.integer, slice)) or k is Ellipsis):
                raise IndexError('pydap only supports indexing with int, '
                                 'slice and Ellipsis objects')
        # pull the data from the array attribute if possible, to avoid
        # downloading coordinate data twice
        array = getattr(self.array, 'array', self.array)
        result = robust_getitem(array, key, catch=ValueError)
        # pydap doesn't squeeze axes automatically like numpy
        axis = tuple(n for n, k in enumerate(key)
                     if isinstance(k, (int, np.integer)))
        result = np.squeeze(result, axis)
        return result


class PydapDataStore(AbstractDataStore):
    """Store for accessing OpenDAP datasets with pydap.

    This store provides an alternative way to access OpenDAP datasets that may
    be useful if the netCDF4 library is not available.
    """
    def __init__(self, url):
        import pydap.client
        self.ds = pydap.client.open_url(url)

    def open_store_variable(self, var):
        data = indexing.LazilyIndexedArray(PydapArrayWrapper(var))
        return Variable(var.dimensions, data, var.attributes)

    def get_variables(self):
        return FrozenOrderedDict((k, self.open_store_variable(v))
                                 for k, v in self.ds.iteritems())

    def get_attrs(self):
        return Frozen(self.ds.attributes)

    def get_dimensions(self):
        return Frozen(self.ds.dimensions)
