/*
 * file: inc.c
 *
 * This file effectively encapsulates functionality of incrementing values while mainting OOP like privateness
 *
 * Author: T0FuZ
 */

#include <stdio.h>


// Remember static defined outside functions makes these variables hidden from other variables
// effectively making this as module or class

// Bonus question: what can we do to make call_counter == effective_call_counter to save from making non-functional call

static int call_counter = 0;            // track every call to function, even if its the non-adding, e.g. simply returning
                                        // from recursion
static int effective_call_counter = 0;  // incrases if value is added e.g. call is making something useful

// 'private' function, this way we can create functions that are not accessible from other sources
static void inc_internal(int *value, int times) {
    call_counter++;
    if (times > 0){
        (*value)++;                     // increase target counter
      
        effective_call_counter++;
        inc_internal(value, times - 1); // recursion
    }
}

// public 'setter-like' function to increment a value
void inc(int *value, int times) {
    inc_internal(value, times);
}

// public 'getter-like' function to access the interal call counter
int get_inc_calls(void) {
    return call_counter;
}

int get_effective_inc_calls(void) {
    return effective_call_counter;
}
