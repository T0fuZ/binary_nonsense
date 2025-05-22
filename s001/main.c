/*
    Sample of static in function, variable that wont be destroyed despite function exiting!
    also recursion example, function calls itself
    also not very commond, using pointer in recursion
    There is no prtacical value in increasing value like this, but its just to show
    how flexible C really is, try to wrap yoru head around it, how you can construct things
    and then you can apply this knowledge in ways nobody cant even follow...
    
    // T0FuZ
    
*/
#include <stdio.h>

int inc(int *value, int times) {
    static int counter = 0; // keep counter of this call
    // this is set only once when first time function called
    // this can be very useful

    if (times > 0) {
        (*value)++;
        counter++; // only increase when something actually increased
        inc(value, times -1);
    }
    return counter; // the final caller gets total counts
}

int main() {
    int a = 0, b = 100;
    int total_calls = 0;
    
    inc(&a, 5); // a = 5
    total_calls = inc(&b,3); // b = 103, total calls = 5 + 3
    printf("a = %d\n", a);
    printf("b = %d\n", b);
    printf("Total calls to inc(): %d\n", total_calls);
}
