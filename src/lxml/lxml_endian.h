#ifndef PY_BIG_ENDIAN

/* STOP INCLUDING THIS FILE !  DO NOT USE IT IN NEW CODE ! */
/* Left only for legacy purposes - this file is no longer used. */

#ifdef _MSC_VER
#pragma message ("Please do not include 'lxml_endian.h'. It is no longer used nor needed.")
typedef unsigned __int32 uint32_t;
#else
#warning Please do not include 'lxml_endian.h'. It is no longer used nor needed.
#include <stdint.h>
#endif

static CYTHON_INLINE int _lx__is_big_endian(void) {
    union {uint32_t i; char c[4];} x = {0x01020304};
    return x.c[0] == 1;
}
#define PY_BIG_ENDIAN _lx__is_big_endian()
#endif
