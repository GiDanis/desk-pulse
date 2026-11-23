/* Diagnostic preload only: observe the actual context on its first swap.
 * No Qt/Python callback, GL state changes, EGL initialization or new context.
 * Build: cc -shared -fPIC -O2 -Wall -Wextra -o gl-probe.so aquarium_gl_probe.c -ldl -pthread
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef void *Handle;
typedef unsigned int Bool;
typedef const unsigned char *(*GetString)(unsigned int);
static pthread_once_t once = PTHREAD_ONCE_INIT;
static Bool (*swap_fn)(Handle, Handle);
static Handle (*current_fn)(void);
static void *(*proc_fn)(const char *);
static Bool (*query_context_fn)(Handle, Handle, int, int *);
static Bool (*choose_config_fn)(Handle, const int *, Handle *, int, int *);
static Bool (*config_attr_fn)(Handle, Handle, int, int *);
static atomic_int captured;

static void resolve(void)
{
    /* Qt can load its dependencies RTLD_LOCAL: use the already loaded EGL. */
    Handle egl = dlopen("libEGL.so.1", RTLD_LAZY | RTLD_NOLOAD);
    if (!egl) return;
    swap_fn = dlsym(egl, "eglSwapBuffers");
    current_fn = dlsym(egl, "eglGetCurrentContext");
    proc_fn = dlsym(egl, "eglGetProcAddress");
    query_context_fn = dlsym(egl, "eglQueryContext");
    choose_config_fn = dlsym(egl, "eglChooseConfig");
    config_attr_fn = dlsym(egl, "eglGetConfigAttrib");
}

static void string(FILE *f, const char *s)
{
    if (!s) { fputs("null", f); return; }
    fputc('"', f);
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
        if (*p == '"' || *p == '\\') fputc('\\', f);
        if (*p < 32) fprintf(f, "\\u%04x", *p); else fputc(*p, f);
    }
    fputc('"', f);
}

Bool eglSwapBuffers(Handle display, Handle surface)
{
    pthread_once(&once, resolve);
    const char *path = getenv("SMARTPC_GL_PROBE_FILE");
    if (path && current_fn && proc_fn && current_fn() && !atomic_exchange(&captured, 1)) {
        GetString get = (GetString)proc_fn("glGetString");
        FILE *f = fopen(path, "w");
        if (f) {
            fputs("{\"scope\":\"native first swap, current render context; no GL state mutation\",\"pid\":", f);
            fprintf(f, "%ld", (long)getpid());
            const unsigned int enums[] = {0x1f00, 0x1f01, 0x1f02, 0x8b8c};
            const char *names[] = {"vendor", "renderer", "version", "glsl"};
            for (int i = 0; i < 4; ++i) {
                fprintf(f, ",\"%s\":", names[i]);
                string(f, get ? (const char *)get(enums[i]) : NULL);
            }
            int id = 0, count = 0;
            Handle cfg = NULL;
            if (query_context_fn && choose_config_fn && config_attr_fn &&
                query_context_fn(display, current_fn(), 0x3028, &id)) {
                const int attrs[] = {0x3028, id, 0x3038};
                if (choose_config_fn(display, attrs, &cfg, 1, &count) && count == 1) {
                    fprintf(f, ",\"eglConfig\":{\"id\":%d", id);
                    const int keys[] = {0x3024,0x3023,0x3022,0x3021,0x3025,0x3026,0x3031,0x3033,0x3040,0x302e};
                    const char *labels[] = {"red","green","blue","alpha","depth","stencil","samples","surfaceType","renderableType","nativeVisualId"};
                    for (int i = 0; i < 10; ++i) {
                        int value = 0;
                        if (config_attr_fn(display, cfg, keys[i], &value))
                            fprintf(f, ",\"%s\":%d", labels[i], value);
                    }
                    fputc('}', f);
                }
            }
            fputs("}\n", f);
            fclose(f);
        }
    }
    return swap_fn ? swap_fn(display, surface) : 0;
}
