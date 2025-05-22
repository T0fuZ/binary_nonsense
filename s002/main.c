/*
main.c
gcc -o prog.exe main.c inc.c



expected output:
a = 5
b = 103
Total calls to inc(): 10
Total effective calls to inc(): 8


 */

#include <stdio.h>
#include "inc.h"       // public interface for incrementation module

int main() {
    int a = 0, b = 100;

    inc(&a, 5);        // a = 5
    inc(&b, 3);        // b = 103

    printf("a = %d\n", a);
    printf("b = %d\n", b);
    printf("Total calls to inc(): %d\n", get_inc_calls());
    printf("Total effective calls to inc(): %d\n", get_effective_inc_calls());

    return 0;
}

