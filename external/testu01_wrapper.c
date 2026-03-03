/*
 * VTRNG TestU01 Wrapper
 * 
 * Reads raw bytes from a binary file and feeds them to
 * TestU01's SmallCrush, Crush, or BigCrush.
 *
 * Build:
 *   gcc -O2 -o testu01_vtrng testu01_wrapper.c \
 *       -I/usr/include -L/usr/lib -ltestu01 -lprobdist -lmylib -lm
 *
 * Install TestU01 first:
 *   git clone https://github.com/umontreal-simul/TestU01-2009.git
 *   cd TestU01-2009 && ./configure && make && sudo make install
 *
 * Usage:
 *   python -m vtrng export -o random.bin --size 100
 *   ./testu01_vtrng random.bin small    # SmallCrush (~30 sec)
 *   ./testu01_vtrng random.bin crush    # Crush (~30 min)
 *   ./testu01_vtrng random.bin big      # BigCrush (~4 hours)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* TestU01 headers */
#include "unif01.h"
#include "ulcg.h"
#include "bbattery.h"

/* File-backed random source */
static FILE *rng_file = NULL;
static long file_size = 0;
static long bytes_read = 0;

static double file_rng_get_u01(void *param, void *state) {
    (void)param;
    (void)state;
    
    uint32_t val;
    size_t n = fread(&val, sizeof(uint32_t), 1, rng_file);
    bytes_read += 4;
    
    if (n != 1 || bytes_read >= file_size) {
        /* Wrap around if we run out */
        fseek(rng_file, 0, SEEK_SET);
        bytes_read = 0;
        if (n != 1) {
            n = fread(&val, sizeof(uint32_t), 1, rng_file);
            bytes_read += 4;
        }
    }
    
    return (double)val / 4294967296.0;
}

static unsigned long file_rng_get_bits(void *param, void *state) {
    (void)param;
    (void)state;
    
    uint32_t val;
    size_t n = fread(&val, sizeof(uint32_t), 1, rng_file);
    bytes_read += 4;
    
    if (n != 1 || bytes_read >= file_size) {
        fseek(rng_file, 0, SEEK_SET);
        bytes_read = 0;
        if (n != 1) {
            fread(&val, sizeof(uint32_t), 1, rng_file);
            bytes_read += 4;
        }
    }
    
    return (unsigned long)val;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <binary_file> [small|crush|big]\n", argv[0]);
        fprintf(stderr, "\nGenerate input with:\n");
        fprintf(stderr, "  python -m vtrng export -o random.bin --size 100\n");
        return 1;
    }
    
    const char *filename = argv[1];
    const char *mode = (argc >= 3) ? argv[2] : "small";
    
    rng_file = fopen(filename, "rb");
    if (!rng_file) {
        fprintf(stderr, "Cannot open %s\n", filename);
        return 1;
    }
    
    /* Get file size */
    fseek(rng_file, 0, SEEK_END);
    file_size = ftell(rng_file);
    fseek(rng_file, 0, SEEK_SET);
    
    printf("VTRNG TestU01 Wrapper\n");
    printf("File: %s (%ld bytes)\n", filename, file_size);
    printf("Suite: %s\n\n", mode);
    
    /* Create TestU01 generator object */
    unif01_Gen *gen = unif01_CreateExternGenBits(
        "VTRNG",
        file_rng_get_u01,
        file_rng_get_bits
    );
    
    /* Run selected battery */
    if (strcmp(mode, "small") == 0) {
        printf("Running SmallCrush (15 tests, ~30 seconds)...\n\n");
        bbattery_SmallCrush(gen);
    } else if (strcmp(mode, "crush") == 0) {
        printf("Running Crush (96 tests, ~30 minutes)...\n\n");
        printf("Recommended: generate at least 100 MB of data.\n\n");
        bbattery_Crush(gen);
    } else if (strcmp(mode, "big") == 0) {
        printf("Running BigCrush (160 tests, ~4 hours)...\n\n");
        printf("Recommended: generate at least 500 MB of data.\n\n");
        bbattery_BigCrush(gen);
    } else {
        fprintf(stderr, "Unknown mode: %s (use small, crush, or big)\n", mode);
        fclose(rng_file);
        return 1;
    }
    
    unif01_DeleteExternGenBits(gen);
    fclose(rng_file);
    
    return 0;
}