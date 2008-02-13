################################################################################
# ObjectPath

ctypedef struct _ObjectPath:
    char* href
    char* name
    Py_ssize_t index


cdef class ObjectPath:
    """ObjectPath(path)
    Immutable object that represents a compiled object path.

    Example for a path: 'root.child[1].{other}child[25]'
    """
    cdef readonly object find
    cdef object _path
    cdef object _path_str
    cdef _ObjectPath*  _c_path
    cdef Py_ssize_t _path_len
    def __init__(self, path):
        if python._isString(path):
            self._path = _parseObjectPathString(path)
            self._path_str = path
        else:
            self._path = _parseObjectPathList(path)
            self._path_str = '.'.join(path)
        self._path_len = python.PyList_GET_SIZE(self._path)
        self._c_path = _buildObjectPathSegments(self._path)
        self.find = self.__call__

    def __dealloc__(self):
        if self._c_path is not NULL:
            python.PyMem_Free(self._c_path)

    def __str__(self):
        return self._path_str

    def __call__(self, _Element root not None, *default):
        """Follow the attribute path in the object structure and return the
        target attribute value.

        If it it not found, either returns a default value (if one was passed
        as second argument) or raises AttributeError.
        """
        cdef Py_ssize_t use_default
        use_default = python.PyTuple_GET_SIZE(default)
        if use_default == 1:
            default = python.PyTuple_GET_ITEM(default, 0)
            python.Py_INCREF(default)
            use_default = 1
        elif use_default > 1:
            raise TypeError("invalid number of arguments: needs one or two")
        return _findObjectPath(root, self._c_path, self._path_len,
                               default, use_default)

    def hasattr(self, _Element root not None):
        "hasattr(self, root)"
        try:
            _findObjectPath(root, self._c_path, self._path_len, None, 0)
        except AttributeError:
            return False
        return True

    def setattr(self, _Element root not None, value):
        """setattr(self, root, value)

        Set the value of the target element in a subtree.

        If any of the children on the path does not exist, it is created.
        """
        _createObjectPath(root, self._c_path, self._path_len, 1, value)

    def addattr(self, _Element root not None, value):
        """addattr(self, root, value)

        Append a value to the target element in a subtree.

        If any of the children on the path does not exist, it is created.
        """
        _createObjectPath(root, self._c_path, self._path_len, 0, value)

cdef object __MATCH_PATH_SEGMENT
__MATCH_PATH_SEGMENT = re.compile(
    r"(\.?)\s*(?:\{([^}]*)\})?\s*([^.{}\[\]\s]+)\s*(?:\[\s*([-0-9]+)\s*\])?",
    re.U).match

cdef object _RELATIVE_PATH_SEGMENT
_RELATIVE_PATH_SEGMENT = (None, None, 0)

cdef _parseObjectPathString(path):
    """Parse object path string into a (ns, name, index) list.
    """
    cdef bint has_dot
    new_path = []
    path = cetree.utf8(path.strip())
    if path == '.':
        return [_RELATIVE_PATH_SEGMENT]
    path_pos = 0
    while python.PyString_GET_SIZE(path) > 0:
        match = __MATCH_PATH_SEGMENT(path, path_pos)
        if match is None:
            break

        dot, ns, name, index = match.groups()
        if index is None or python.PyString_GET_SIZE(index) == 0:
            index = 0
        else:
            index = python.PyNumber_Int(index)
        has_dot = _cstr(dot)[0] == c'.'
        if python.PyList_GET_SIZE(new_path) == 0:
            if has_dot:
                # path '.child' => ignore root
                python.PyList_Append(new_path, _RELATIVE_PATH_SEGMENT)
            elif index != 0:
                raise ValueError("index not allowed on root node")
        elif not has_dot:
            raise ValueError("invalid path")
        python.PyList_Append(new_path, (ns, name, index))
        
        path_pos = match.end()
    if python.PyList_GET_SIZE(new_path) == 0 or \
           python.PyString_GET_SIZE(path) > path_pos:
        raise ValueError("invalid path")
    return new_path

cdef _parseObjectPathList(path):
    """Parse object path sequence into a (ns, name, index) list.
    """
    cdef char* index_pos
    cdef char* index_end
    cdef char* c_name
    new_path = []
    for item in path:
        item = item.strip()
        if python.PyList_GET_SIZE(new_path) == 0 and item == '':
            # path '.child' => ignore root
            ns = name = None
            index = 0
        else:
            ns, name = cetree.getNsTag(item)
            c_name = _cstr(name)
            index_pos = cstd.strchr(c_name, c'[')
            if index_pos is NULL:
                index = 0
            else:
                index_end = cstd.strchr(index_pos + 1, c']')
                if index_end is NULL:
                    raise ValueError("index must be enclosed in []")
                index = python.PyNumber_Int(
                    python.PyString_FromStringAndSize(
                        index_pos + 1, <Py_ssize_t>(index_end - index_pos - 1)))
                if python.PyList_GET_SIZE(new_path) == 0 and index != 0:
                    raise ValueError("index not allowed on root node")
                name = python.PyString_FromStringAndSize(
                    c_name, <Py_ssize_t>(index_pos - c_name))
        python.PyList_Append(new_path, (ns, name, index))
    if python.PyList_GET_SIZE(new_path) == 0:
        raise ValueError("invalid path")
    return new_path

cdef _ObjectPath* _buildObjectPathSegments(path_list) except NULL:
    cdef _ObjectPath* c_path
    cdef _ObjectPath* c_path_segments
    c_path_segments = <_ObjectPath*>python.PyMem_Malloc(
        sizeof(_ObjectPath) * python.PyList_GET_SIZE(path_list))
    if c_path_segments is NULL:
        python.PyErr_NoMemory()
    c_path = c_path_segments
    for href, name, index in path_list:
        if href is None:
            c_path[0].href = NULL
        else:
            c_path[0].href = _cstr(href)
        if name is None:
            c_path[0].name = NULL
        else:
            c_path[0].name = _cstr(name)
        c_path[0].index = index
        c_path = c_path + 1
    return c_path_segments

cdef _findObjectPath(_Element root, _ObjectPath* c_path, Py_ssize_t c_path_len,
                     default_value, int use_default):
    """Follow the path to find the target element.
    """
    cdef tree.xmlNode* c_node
    cdef char* c_href
    cdef char* c_name
    cdef Py_ssize_t c_index
    c_node = root._c_node
    c_name = c_path[0].name
    c_href = c_path[0].href
    if c_href is NULL or c_href[0] == c'\0':
        c_href = tree._getNs(c_node)
    if not cetree.tagMatches(c_node, c_href, c_name):
        raise ValueError(
            "root element does not match: need %s, got %s" %
            (cetree.namespacedNameFromNsName(c_href, c_name), root.tag))

    while c_node is not NULL:
        c_path_len = c_path_len - 1
        if c_path_len <= 0:
            break

        c_path = c_path + 1
        if c_path[0].href is not NULL:
            c_href = c_path[0].href # otherwise: keep parent namespace
        c_name = c_path[0].name
        c_index = c_path[0].index

        if c_index < 0:
            c_node = c_node.last
        else:
            c_node = c_node.children
        c_node = _findFollowingSibling(c_node, c_href, c_name, c_index)

    if c_node is not NULL:
        return cetree.elementFactory(root._doc, c_node)
    elif use_default:
        return default_value
    else:
        tag = cetree.namespacedNameFromNsName(c_href, c_name)
        raise AttributeError("no such child: " + tag)

cdef _createObjectPath(_Element root, _ObjectPath* c_path,
                       Py_ssize_t c_path_len, int replace, value):
    """Follow the path to find the target element, build the missing children
    as needed and set the target element to 'value'.  If replace is true, an
    existing value is replaced, otherwise the new value is added.
    """
    cdef _Element child
    cdef tree.xmlNode* c_node
    cdef tree.xmlNode* c_child
    cdef char* c_href
    cdef char* c_name
    cdef Py_ssize_t c_index
    if c_path_len == 1:
        raise TypeError("cannot update root node")

    c_node = root._c_node
    c_name = c_path[0].name
    c_href = c_path[0].href
    if c_href is NULL or c_href[0] == c'\0':
        c_href = tree._getNs(c_node)
    if not cetree.tagMatches(c_node, c_href, c_name):
        raise ValueError(
            "root element does not match: need %s, got %s" %
            (cetree.namespacedNameFromNsName(c_href, c_name), root.tag))

    while c_path_len > 1:
        c_path_len = c_path_len - 1
        c_path = c_path + 1
        if c_path[0].href is not NULL:
            c_href = c_path[0].href # otherwise: keep parent namespace
        c_name = c_path[0].name
        c_index = c_path[0].index

        if c_index < 0:
            c_child = c_node.last
        else:
            c_child = c_node.children
        c_child = _findFollowingSibling(c_child, c_href, c_name, c_index)

        if c_child is not NULL:
            c_node = c_child
        elif c_index != 0:
            raise TypeError(
                "creating indexed path attributes is not supported")
        elif c_path_len == 1:
            _appendValue(cetree.elementFactory(root._doc, c_node),
                         cetree.namespacedNameFromNsName(c_href, c_name),
                         value)
            return
        else:
            child = cetree.makeSubElement(
                cetree.elementFactory(root._doc, c_node),
                cetree.namespacedNameFromNsName(c_href, c_name),
                None, None, None, None)
            c_node = child._c_node

    # if we get here, the entire path was already there
    if replace:
        element = cetree.elementFactory(root._doc, c_node)
        _replaceElement(element, value)
    else:
        _appendValue(cetree.elementFactory(root._doc, c_node.parent),
                     cetree.namespacedName(c_node), value)

cdef _buildDescendantPaths(tree.xmlNode* c_node, prefix_string):
    """Returns a list of all descendant paths.
    """
    tag = cetree.namespacedName(c_node)
    if prefix_string:
        if prefix_string[-1] != '.':
            prefix_string = prefix_string + '.'
        prefix_string = prefix_string + tag
    else:
        prefix_string = tag
    path = [prefix_string]
    path_list = []
    _recursiveBuildDescendantPaths(c_node, path, path_list)
    return path_list

cdef _recursiveBuildDescendantPaths(tree.xmlNode* c_node, path, path_list):
    """Fills the list 'path_list' with all descendant paths, initial prefix
    being in the list 'path'.
    """
    cdef python.PyObject* dict_result
    cdef tree.xmlNode* c_child
    cdef char* c_href
    python.PyList_Append(path_list, '.'.join(path))
    tags = {}
    c_href = tree._getNs(c_node)
    c_child = c_node.children
    while c_child is not NULL:
        while c_child.type != tree.XML_ELEMENT_NODE:
            c_child = c_child.next
            if c_child is NULL:
                return
        if c_href is tree._getNs(c_child):
            tag = c_child.name
        elif c_href is not NULL and tree._getNs(c_child) is NULL:
            # special case: parent has namespace, child does not
            tag = '{}' + c_child.name
        else:
            tag = cetree.namespacedName(c_child)
        dict_result = python.PyDict_GetItem(tags, tag)
        if dict_result is NULL:
            count = 0
        else:
            count = (<object>dict_result) + 1
        python.PyDict_SetItem(tags, tag, count)
        if count > 0:
            tag = tag + '[%d]' % count
        python.PyList_Append(path, tag)
        _recursiveBuildDescendantPaths(c_child, path, path_list)
        del path[-1]
        c_child = c_child.next
