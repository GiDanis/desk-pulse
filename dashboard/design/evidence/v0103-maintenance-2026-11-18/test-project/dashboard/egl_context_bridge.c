/* Bridge Qt's direct GL capability queries to its current EGL context.
 * Only these two query entrypoints are interposed. Rendering, EGL/GBM,
 * allocation and synchronization continue through the existing driver stack.
 * No Qt private ABI; build as a device-local shared library with -ldl -pthread.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>

typedef const unsigned char *(*StringQuery)(unsigned int);
typedef void (*IntegerQuery)(unsigned int, int *);
static pthread_once_t once = PTHREAD_ONCE_INIT;
static void *(*current_context)(void);
static StringQuery egl_string;
static IntegerQuery egl_integer;
static StringQuery other_string;
static IntegerQuery other_integer;

static void resolve_queries(void)
{
    /* Use the already loaded EGL selected by Qt, never initialize a display. */
    void *egl = dlopen("libEGL.so.1", RTLD_LAZY | RTLD_NOLOAD);
    if (egl) {
        void *(*get_proc)(const char *) = dlsym(egl, "eglGetProcAddress");
        current_context = dlsym(egl, "eglGetCurrentContext");
        if (get_proc) {
            egl_string = (StringQuery)get_proc("glGetString");
            egl_integer = (IntegerQuery)get_proc("glGetIntegerv");
        }
    }
    other_string = (StringQuery)dlsym(RTLD_NEXT, "glGetString");
    other_integer = (IntegerQuery)dlsym(RTLD_NEXT, "glGetIntegerv");
}

const unsigned char *glGetString(unsigned int name)
{
    pthread_once(&once, resolve_queries);
    if (current_context && current_context() && egl_string && egl_string != glGetString)
        return egl_string(name);
    return other_string && other_string != glGetString ? other_string(name) : 0;
}

void glGetIntegerv(unsigned int name, int *value)
{
    pthread_once(&once, resolve_queries);
    if (current_context && current_context() && egl_integer && egl_integer != glGetIntegerv) {
        egl_integer(name, value);
        return;
    }
    if (other_integer && other_integer != glGetIntegerv)
        other_integer(name, value);
}
