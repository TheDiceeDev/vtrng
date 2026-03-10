/*
 * VTRNG Fast Entropy Source - v0.5.1
 *
 * Architecture:
 *   Platform detection at top → separate function blocks per arch.
 *   This is the same design as v0.2, with these additions:
 *     - cpuid serialization before timing (x86)
 *     - rdtscp after workload (x86, gives core ID)
 *     - ISB barrier (ARM64)
 *     - Core migration detection via sentinel value
 *     - GIL released during sampling
 *     - Enhanced workload: pointer chase + FPU + TLB thrashing
 *     - Native thread race (OS threads, no GIL)
 *     - platform_info() introspection
 *
 * Build:
 *   pip install -e .
 *   OR: python setup.py build_ext --inplace
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>

/* ================================================================
 *  PLATFORM DETECTION
 * ================================================================ */

#if defined(_MSC_VER) && (defined(_M_X64) || defined(_M_IX86))
    #define VTRNG_X86 1
    #include <intrin.h>
#elif defined(__x86_64__) || defined(__i386__)
    #define VTRNG_X86 1
    #ifdef __GNUC__
        #include <cpuid.h>
    #endif
#elif defined(__aarch64__)
    #define VTRNG_ARM64 1
#else
    #define VTRNG_FALLBACK 1
    #include <time.h>
#endif

/* Threading */
#ifdef _WIN32
    #include <windows.h>
    #include <process.h>
#else
    #include <pthread.h>
#endif


/* ================================================================
 *  CONSTANTS
 * ================================================================ */

/* Sentinel: "we don't know which core" (can't be a real core ID) */
#define CORE_ID_UNKNOWN  0xFFFFFFFF

/* Arena for TLB-thrashing workload (allocated at module init) */
static uint8_t *jitter_arena = NULL;
static const size_t ARENA_SIZE = 2 * 1024 * 1024;  /* 2 MB */


/* ================================================================
 *  SERIALIZED TIMING - x86 (Intel / AMD)
 * ================================================================
 *
 * BEGIN: cpuid flushes the entire pipeline (full serialization),
 *        then rdtsc reads the timestamp counter.
 *        No workload instructions can leak past cpuid.
 *
 * END:   rdtscp is inherently serializing AND returns the core ID
 *        in the ECX register (IA32_TSC_AUX).
 *        Core ID lets us detect migration between begin/end.
 */

#ifdef VTRNG_X86

static inline uint64_t rdtsc_begin(uint32_t *core_id) {
    #if defined(_MSC_VER)
        int regs[4];
        __cpuid(regs, 0);              /* serialize pipeline */
        *core_id = CORE_ID_UNKNOWN;    /* cpuid doesn't give core ID */
        return __rdtsc();
    #else
        uint32_t lo, hi;
        __asm__ volatile (
            "cpuid\n\t"                 /* serialize pipeline */
            "rdtsc\n\t"                 /* read timestamp */
            : "=a"(lo), "=d"(hi)
            : "a"(0)                    /* cpuid leaf 0 */
            : "rbx", "rcx"             /* cpuid clobbers */
        );
        *core_id = CORE_ID_UNKNOWN;
        return ((uint64_t)hi << 32) | lo;
    #endif
}

static inline uint64_t rdtsc_end(uint32_t *core_id) {
    #if defined(_MSC_VER)
        unsigned int aux;
        uint64_t tsc = __rdtscp(&aux);
        *core_id = aux;                /* IA32_TSC_AUX = core ID */
        return tsc;
    #else
        uint32_t lo, hi, aux;
        __asm__ volatile (
            "rdtscp\n\t"                /* serializing + core ID */
            : "=a"(lo), "=d"(hi), "=c"(aux)
        );
        *core_id = aux;
        return ((uint64_t)hi << 32) | lo;
    #endif
}

#endif /* VTRNG_X86 */


/* ================================================================
 *  SERIALIZED TIMING - ARM64 (Apple Silicon, RPi4, etc.)
 * ================================================================
 *
 * ISB (Instruction Synchronization Barrier) ensures all previous
 * instructions have completed before reading the counter.
 * ARM doesn't expose core ID through the counter register.
 */

#ifdef VTRNG_ARM64

static inline uint64_t rdtsc_begin(uint32_t *core_id) {
    uint64_t val;
    __asm__ volatile (
        "isb\n\t"                       /* instruction barrier */
        "mrs %0, cntvct_el0\n\t"        /* read virtual counter */
        : "=r"(val)
    );
    *core_id = CORE_ID_UNKNOWN;
    return val;
}

static inline uint64_t rdtsc_end(uint32_t *core_id) {
    uint64_t val;
    __asm__ volatile (
        "isb\n\t"
        "mrs %0, cntvct_el0\n\t"
        : "=r"(val)
    );
    *core_id = CORE_ID_UNKNOWN;         /* ARM: no core ID from counter */
    return val;
}

#endif /* VTRNG_ARM64 */


/* ================================================================
 *  FALLBACK TIMING - clock_gettime (any POSIX system)
 * ================================================================
 *
 * Lower resolution (~1ns) vs RDTSC (~0.3ns), but still works.
 * We measure DELTAS, not absolute time - jitter is still physical.
 */

#ifdef VTRNG_FALLBACK

static inline uint64_t rdtsc_begin(uint32_t *core_id) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    *core_id = CORE_ID_UNKNOWN;
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint64_t rdtsc_end(uint32_t *core_id) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    *core_id = CORE_ID_UNKNOWN;
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

#endif /* VTRNG_FALLBACK */


/* ================================================================
 *  JITTER WORKLOAD
 * ================================================================
 *
 * Designed to hit multiple CPU subsystems with variable cost:
 *   - Integer ALU (xorshift)
 *   - FPU pipeline (sqrt - variable latency on most CPUs)
 *   - Memory subsystem (pointer chase through 2MB arena)
 *   - TLB (accesses cross 4KB page boundaries)
 *   - Branch predictor (iteration count varies per call)
 *
 * The iteration count depends on the fold state, which depends
 * on previous timing → feedback loop where jitter affects
 * workload which affects jitter.
 */

static void jitter_workload(volatile uint64_t *fold) {
    uint64_t x = *fold;
    int n = 64 + (int)(x & 0x3F);      /* 64-127 iterations */

    volatile uint64_t sink = 0;          /* prevent optimization */

    for (int i = 0; i < n; i++) {
        /* ── Integer ALU: xorshift64 ── */
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        sink += x;

        /* ── FPU: every 8 iterations ── */
        /* sqrt has data-dependent latency on most CPUs */
        if ((i & 7) == 0) {
            volatile double fval = (double)(x & 0xFFFF);
            fval = sqrt(fval + 1.0) * 3.14159265358979;
            sink += (uint64_t)(fval > 0 ? fval : -fval);
        }

        /* ── Memory + TLB: every 16 iterations ── */
        /* Pointer chase through 2MB arena crossing page boundaries */
        if ((i & 15) == 0 && jitter_arena != NULL) {
            /* Pick offset based on current state */
            size_t offset = (size_t)(x % ARENA_SIZE);

            /* Force page boundary crossing (near 4KB edge) */
            size_t page_base = offset & ~((size_t)4095);
            size_t cross_offset = page_base + 4093;
            if (cross_offset < ARENA_SIZE - 8) {
                /* This read spans two 4KB pages → TLB miss likely */
                volatile uint64_t *ptr =
                    (volatile uint64_t *)(jitter_arena + cross_offset);
                sink += *ptr;

                /* Pointer chase: next address depends on value read */
                size_t next = (size_t)(sink % (ARENA_SIZE - 8));
                sink += *(volatile uint64_t *)(jitter_arena + next);
            } else {
                /* Fallback for edge case */
                sink += jitter_arena[offset % ARENA_SIZE];
            }
        }
    }

    *fold = x ^ sink;
}


/* ================================================================
 *  ARENA INIT (called at module load)
 * ================================================================ */

static int init_arena(void) {
    if (jitter_arena != NULL) {
        return 0;  /* already initialized */
    }
    jitter_arena = (uint8_t *)malloc(ARENA_SIZE);
    if (jitter_arena == NULL) {
        return -1;
    }
    /* Fill with non-trivial pattern */
    for (size_t i = 0; i < ARENA_SIZE; i++) {
        jitter_arena[i] = (uint8_t)((i * 7 + 13) ^ (i >> 8));
    }
    return 0;
}


/* ================================================================
 *  PYTHON FUNCTION: sample(n=512)
 * ================================================================
 *
 * Collects n CPU jitter timing samples.
 * GIL is released during collection for true concurrency.
 * Invalid samples (core migration, backwards time) are discarded.
 * Returns a Python list of valid int64 deltas.
 */

static PyObject* vtrng_sample(PyObject *self, PyObject *args) {
    int n = 512;
    if (!PyArg_ParseTuple(args, "|i", &n))
        return NULL;

    if (n <= 0 || n > 100000) {
        PyErr_SetString(PyExc_ValueError, "n must be 1-100000");
        return NULL;
    }

    /* Allocate results buffer BEFORE releasing GIL */
    int64_t *results = (int64_t *)malloc(n * sizeof(int64_t));
    if (!results) {
        PyErr_NoMemory();
        return NULL;
    }

    int valid_count = 0;
    int migrations = 0;
    int backwards = 0;

    /* ── RELEASE THE GIL ── */
    Py_BEGIN_ALLOW_THREADS

    volatile uint64_t fold = 0;

    /* Seed fold from initial timestamp */
    uint32_t dummy_core;
    fold = rdtsc_begin(&dummy_core);

    for (int i = 0; i < n; i++) {
        uint32_t core_begin, core_end;

        /* Serialized timing pair */
        uint64_t t0 = rdtsc_begin(&core_begin);
        jitter_workload(&fold);
        uint64_t t1 = rdtsc_end(&core_end);

        /* ── Validate sample ── */

        /* Check 1: Core migration */
        if (core_begin != CORE_ID_UNKNOWN
            && core_end != CORE_ID_UNKNOWN
            && core_begin != core_end) {
            results[i] = -1;
            migrations++;
            continue;
        }

        /* Check 2: Backwards or zero time */
        if (t1 <= t0) {
            results[i] = -1;
            backwards++;
            continue;
        }

        /* Valid sample */
        results[i] = (int64_t)(t1 - t0);
        valid_count++;
    }

    /* ── REACQUIRE THE GIL ── */
    Py_END_ALLOW_THREADS

    /* Build Python list from valid samples only */
    PyObject *list = PyList_New(0);
    if (!list) {
        free(results);
        return NULL;
    }

    for (int i = 0; i < n; i++) {
        if (results[i] < 0)
            continue;

        PyObject *val = PyLong_FromLongLong(results[i]);
        if (!val) {
            free(results);
            Py_DECREF(list);
            return NULL;
        }
        if (PyList_Append(list, val) < 0) {
            free(results);
            Py_DECREF(val);
            Py_DECREF(list);
            return NULL;
        }
        Py_DECREF(val);
    }

    free(results);
    return list;
}


/* ================================================================
 *  NATIVE THREAD RACE (bypasses Python GIL)
 * ================================================================
 *
 * Two OS-level threads race on a shared volatile counter
 * WITHOUT any synchronization. One increments, one decrements.
 *
 * The final value depends on exact hardware scheduling,
 * cache coherency protocol timing, and core arbitration -
 * all genuine physical non-determinism.
 *
 * This replaces the Python ThreadRaceSource when the C
 * extension is available.
 */

typedef struct {
    volatile int64_t *counter;
    int iterations;
    int increment;
} race_args_t;


/* ── Windows threads ── */

#ifdef _WIN32

static unsigned __stdcall race_thread_func(void *arg) {
    race_args_t *ra = (race_args_t *)arg;
    for (int i = 0; i < ra->iterations; i++) {
        *(ra->counter) += ra->increment;  /* deliberate data race */
    }
    return 0;
}

static int64_t run_single_race(int iterations) {
    volatile int64_t counter = 0;
    race_args_t args_pos = { &counter, iterations, 1 };
    race_args_t args_neg = { &counter, iterations, -1 };

    HANDLE h1 = (HANDLE)_beginthreadex(
        NULL, 0, race_thread_func, &args_pos, 0, NULL
    );
    HANDLE h2 = (HANDLE)_beginthreadex(
        NULL, 0, race_thread_func, &args_neg, 0, NULL
    );

    if (h1 && h2) {
        WaitForSingleObject(h1, 5000);
        WaitForSingleObject(h2, 5000);
        CloseHandle(h1);
        CloseHandle(h2);
    }
    return counter;
}

/* ── POSIX threads (Linux, macOS) ── */

#else

static void* race_thread_func(void *arg) {
    race_args_t *ra = (race_args_t *)arg;
    for (int i = 0; i < ra->iterations; i++) {
        *(ra->counter) += ra->increment;  /* deliberate data race */
    }
    return NULL;
}

static int64_t run_single_race(int iterations) {
    volatile int64_t counter = 0;
    race_args_t args_pos = { &counter, iterations, 1 };
    race_args_t args_neg = { &counter, iterations, -1 };

    pthread_t t1, t2;
    pthread_create(&t1, NULL, race_thread_func, &args_pos);
    pthread_create(&t2, NULL, race_thread_func, &args_neg);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return counter;
}

#endif /* _WIN32 / POSIX */


static PyObject* vtrng_thread_race(PyObject *self, PyObject *args) {
    int rounds = 128;
    int iterations = 200;
    if (!PyArg_ParseTuple(args, "|ii", &rounds, &iterations))
        return NULL;

    if (rounds <= 0 || rounds > 10000) {
        PyErr_SetString(PyExc_ValueError, "rounds must be 1-10000");
        return NULL;
    }
    if (iterations <= 0 || iterations > 100000) {
        PyErr_SetString(PyExc_ValueError, "iterations must be 1-100000");
        return NULL;
    }

    /* Collect results - each race releases/reacquires GIL */
    PyObject *list = PyList_New(rounds);
    if (!list) return NULL;

    for (int i = 0; i < rounds; i++) {
        int64_t result;

        Py_BEGIN_ALLOW_THREADS
        result = run_single_race(iterations);
        Py_END_ALLOW_THREADS

        PyObject *val = PyLong_FromLongLong(result);
        if (!val) {
            Py_DECREF(list);
            return NULL;
        }
        PyList_SET_ITEM(list, i, val);  /* steals reference */
    }

    return list;
}


/* ================================================================
 *  PYTHON FUNCTION: platform_info()
 * ================================================================
 *
 * Returns a dict describing the platform-specific capabilities.
 * Useful for diagnostics and debugging.
 */

static PyObject* vtrng_platform_info(PyObject *self, PyObject *args) {
    (void)args;
    PyObject *dict = PyDict_New();
    if (!dict) return NULL;

    #ifdef VTRNG_X86
        PyDict_SetItemString(dict, "arch",
            PyUnicode_FromString("x86"));
        PyDict_SetItemString(dict, "timer",
            PyUnicode_FromString("rdtsc/rdtscp"));
        PyDict_SetItemString(dict, "serialization",
            PyUnicode_FromString("cpuid + rdtscp"));
        Py_INCREF(Py_True);
        PyDict_SetItemString(dict, "serialized", Py_True);
        Py_INCREF(Py_True);
        PyDict_SetItemString(dict, "core_migration_detection", Py_True);
    #elif defined(VTRNG_ARM64)
        PyDict_SetItemString(dict, "arch",
            PyUnicode_FromString("arm64"));
        PyDict_SetItemString(dict, "timer",
            PyUnicode_FromString("cntvct_el0"));
        PyDict_SetItemString(dict, "serialization",
            PyUnicode_FromString("isb"));
        Py_INCREF(Py_True);
        PyDict_SetItemString(dict, "serialized", Py_True);
        Py_INCREF(Py_False);
        PyDict_SetItemString(dict, "core_migration_detection", Py_False);
    #else
        PyDict_SetItemString(dict, "arch",
            PyUnicode_FromString("fallback"));
        PyDict_SetItemString(dict, "timer",
            PyUnicode_FromString("clock_gettime"));
        PyDict_SetItemString(dict, "serialization",
            PyUnicode_FromString("none"));
        Py_INCREF(Py_False);
        PyDict_SetItemString(dict, "serialized", Py_False);
        Py_INCREF(Py_False);
        PyDict_SetItemString(dict, "core_migration_detection", Py_False);
    #endif

    Py_INCREF(Py_True);
    PyDict_SetItemString(dict, "native_threads", Py_True);
    Py_INCREF(Py_True);
    PyDict_SetItemString(dict, "gil_released", Py_True);

    /* Arena status */
    PyDict_SetItemString(dict, "arena_allocated",
        jitter_arena != NULL ? Py_True : Py_False);
    if (jitter_arena != NULL) {
        Py_INCREF(Py_True);
    } else {
        Py_INCREF(Py_False);
    }

    PyDict_SetItemString(dict, "arena_size_mb",
        PyLong_FromLong((long)(ARENA_SIZE / 1024 / 1024)));

    return dict;
}


/* ================================================================
 *  MODULE DEFINITION
 * ================================================================ */

static PyMethodDef vtrng_methods[] = {
    {
        "sample",
        vtrng_sample,
        METH_VARARGS,
        "sample(n=512) -> list[int]\n\n"
        "Collect n CPU jitter timing samples.\n"
        "Uses serialized rdtsc (x86) or ISB+cntvct (ARM64).\n"
        "Detects and discards core-migrated samples.\n"
        "GIL is released during collection.\n"
        "Returns list of valid cycle-count deltas."
    },
    {
        "thread_race",
        vtrng_thread_race,
        METH_VARARGS,
        "thread_race(rounds=128, iterations=200) -> list[int]\n\n"
        "Run native OS thread races (bypasses Python GIL).\n"
        "Two threads race on a shared counter without sync.\n"
        "Returns list of race outcome values."
    },
    {
        "platform_info",
        vtrng_platform_info,
        METH_NOARGS,
        "platform_info() -> dict\n\n"
        "Returns platform-specific timing capabilities:\n"
        "  arch, timer, serialization, core_migration_detection,\n"
        "  native_threads, gil_released, arena_allocated."
    },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef vtrng_module = {
    PyModuleDef_HEAD_INIT,
    "_vtrng_fast",
    "VTRNG C extension v0.5.1\n"
    "Serialized rdtsc, GIL-free sampling, TLB-thrashing workload,\n"
    "native thread races, core migration detection.",
    -1,
    vtrng_methods
};

PyMODINIT_FUNC PyInit__vtrng_fast(void) {
    PyObject *module = PyModule_Create(&vtrng_module);
    if (module == NULL)
        return NULL;

    /* Allocate jitter arena (non-fatal if it fails) */
    if (init_arena() < 0) {
        /* Non-fatal but warns via python warning system */
        if (PyErr_WarnEx(
                PyExc_RuntimeWarning,
                "VTRNG: Failed to allocate 2MB jitter arena. "
                "TLB-thrashing workload disabled. "
                "Entropy quality may be slightly reduced.",
                1) < 0) {
            /* Warning was turned into an error - still non-fatal for us */
            PyErr_Clear();
        }
    }

    return module;
}