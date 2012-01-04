from libc.limits cimport INT_MAX

from libc.string cimport (
    strlen,
    strstr,
    strchr,
    strrchr,
    strcmp,
    strncmp,
    memcpy,
    memset,
)

from libc.stdio cimport (
    FILE,
    fread,
    feof,
    ferror,
    sprintf,
    printf,
)

from libc.stdlib cimport (
    malloc,
    realloc,
    free,
)
